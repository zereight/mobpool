"""Shared service layer for mobpool CLI and GUI."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import os
import time
from typing import Any, Callable

from mobpool.claims import (
    OwnerInfo,
    prune_expired_claims,
    remove_claim,
    renew_claim,
    resolve_owner,
    write_claim,
)
from mobpool.config import MobpoolConfig
from mobpool.lock import LockTimeoutError, acquire_lock, state_lock
from mobpool.memory import mac_free_memory_pct
from mobpool.platforms.android import AndroidAdapter
from mobpool.platforms.base import DeviceInfo, PlatformAdapter
from mobpool.platforms.ios import IOSAdapter
from mobpool.pool_store import load_pools, save_pools


@dataclass(frozen=True)
class ServiceResult:
    ok: bool
    exit_code: int
    message: str
    data: dict[str, Any] = field(default_factory=dict)


def default_adapters(cfg: MobpoolConfig) -> dict[str, PlatformAdapter]:
    return {
        "ios": IOSAdapter(cfg),
        "android": AndroidAdapter(cfg),
    }


def platforms_for(selection: str) -> list[str]:
    if selection == "all":
        return ["ios", "android"]
    return [selection]


def cap_for(cfg: MobpoolConfig, platform: str) -> int:
    return cfg.ios_cap if platform == "ios" else cfg.android_cap


def adapter_slim_capability(adapter: PlatformAdapter) -> tuple[bool, str]:
    cap_fn = getattr(adapter, "slim_capability", None)
    if callable(cap_fn):
        try:
            result = cap_fn()
            if isinstance(result, tuple) and len(result) == 2:
                return bool(result[0]), str(result[1])
        except Exception:
            pass
    ok, reason = adapter.is_available()
    return ok, ("available" if ok else reason)


def list_platform_devices(adapter: PlatformAdapter) -> list[DeviceInfo]:
    combined_fn = getattr(adapter, "list_all_with_metrics", None)
    if callable(combined_fn):
        return list(combined_fn())
    available = list(adapter.list_available())
    booted_by_id = {dev.device_id: dev for dev in adapter.list_booted()}
    merged: list[DeviceInfo] = []
    seen: set[str] = set()
    for dev in available:
        seen.add(dev.device_id)
        merged.append(booted_by_id.get(dev.device_id, dev))
    for device_id, dev in booted_by_id.items():
        if device_id not in seen:
            merged.append(dev)
    return merged


def resolve_device_owner(
    cfg: MobpoolConfig,
    adapter: PlatformAdapter,
    device_id: str,
    check_app: bool = True,
    *,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> OwnerInfo | None:
    app_fn = adapter.is_app_running if check_app else None
    return resolve_owner(
        cfg,
        device_id,
        app_running_fn=app_fn,
        match_workspace=match_workspace,
        self_owners=self_owners,
    )


def find_device_by_id(
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    preferred_platform: str | None = None,
) -> tuple[PlatformAdapter | None, DeviceInfo | None]:
    order = [preferred_platform] if preferred_platform else ["ios", "android"]
    for plat in order:
        adapter = adapters.get(plat)
        if adapter is None:
            continue
        ok, _ = adapter.is_available()
        if not ok:
            continue
        for dev in adapter.list_available():
            if device_or_runtime_id in (dev.device_id, dev.runtime_id):
                return adapter, dev
    return None, None


def _owner_to_dict(owner: OwnerInfo | None) -> dict[str, Any] | None:
    if owner is None:
        return None
    return {
        "source": owner.source,
        "label": owner.label,
        "is_self": owner.is_self,
        "expires_in_sec": owner.expires_in_sec,
        "display": owner.display(),
    }


def collect_audit(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
    *,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> dict[str, object]:
    prune_expired_claims(cfg)
    pools = load_pools(cfg)
    rows: list[dict[str, object]] = []
    counts: dict[str, int] = {"ios": 0, "android": 0}
    unavailable: dict[str, str] = {}

    for plat in platforms_for(platform_sel):
        adapter = adapters[plat]
        ok, reason = adapter.is_available()
        if not ok:
            unavailable[plat] = reason
            continue
        booted = adapter.list_booted()
        counts[plat] = len(booted)
        pool_set = set(pools.get(plat, []))
        for dev in booted:
            owner = resolve_device_owner(
                cfg,
                adapter,
                dev.device_id,
                check_app=True,
                match_workspace=match_workspace,
                self_owners=self_owners,
            )
            if owner is not None:
                tag = f"claimed:{owner.display()}"
                if dev.device_id in pool_set:
                    tag += " (pool)"
                is_orphan = False
            elif dev.device_id in pool_set:
                tag = "pool"
                is_orphan = False
            else:
                tag = "orphan"
                is_orphan = True
            rows.append(
                {
                    "platform": plat,
                    "device_id": dev.device_id,
                    "target_id": dev.target_id,
                    "name": dev.name,
                    "os_version": dev.os_version,
                    "ram_bytes": dev.ram_bytes,
                    "processes": dev.processes,
                    "cpu_pct": dev.cpu_pct,
                    "slim_status": dev.slim_status,
                    "tag": tag,
                    "is_orphan": is_orphan,
                    "shutdown_hint": adapter.shutdown_hint(dev),
                }
            )

    return {
        "devices": rows,
        "counts": counts,
        "total_booted": sum(counts.values()),
        "caps": {
            "ios": cfg.ios_cap,
            "android": cfg.android_cap,
            "total": cfg.total_cap,
        },
        "pools": pools,
        "free_memory_pct": free_pct_fn(),
        "min_free_pct": cfg.min_free_pct,
        "unavailable": unavailable,
    }


def collect_dashboard_state(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
    *,
    match_workspace: bool = False,
    self_owners: set[str] | None = None,
) -> dict[str, Any]:
    prune_expired_claims(cfg)
    pools = load_pools(cfg)

    def _collect_platform(plat: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        adapter = adapters[plat]
        ok, reason = adapter.is_available()
        can_slim, slim_note = adapter_slim_capability(adapter)
        pool_list = pools.get(plat, [])
        pool_set = set(pool_list)
        if not ok:
            return (
                {
                    "available": False,
                    "reason": reason,
                    "booted_count": 0,
                    "installed_count": 0,
                    "cap": cap_for(cfg, plat),
                    "pool_count": len(pool_list),
                    "can_slim": False,
                    "slim_note": reason,
                },
                [],
            )

        devices = list_platform_devices(adapter)
        rows: list[dict[str, Any]] = []
        booted_count = 0
        for dev in devices:
            is_booted = dev.state == "Booted"
            if is_booted:
                booted_count += 1
            owner = resolve_device_owner(
                cfg,
                adapter,
                dev.device_id,
                check_app=is_booted,
                match_workspace=match_workspace,
                self_owners=self_owners,
            )
            in_pool = dev.device_id in pool_set
            if owner is not None:
                tag = f"claimed:{owner.display()}"
                if in_pool:
                    tag += " (pool)"
                is_orphan = False
            elif is_booted and not in_pool:
                tag = "orphan"
                is_orphan = True
            elif in_pool:
                tag = "pool"
                is_orphan = False
            else:
                tag = "available"
                is_orphan = False

            rows.append(
                {
                    "platform": plat,
                    "device_id": dev.device_id,
                    "runtime_id": dev.runtime_id,
                    "target_id": dev.target_id,
                    "name": dev.name,
                    "os_version": dev.os_version,
                    "state": dev.state,
                    "in_pool": in_pool,
                    "is_orphan": is_orphan,
                    "ram_bytes": dev.ram_bytes,
                    "processes": dev.processes,
                    "cpu_pct": dev.cpu_pct,
                    "slim_status": dev.slim_status,
                    "owner": _owner_to_dict(owner),
                    "tag": tag,
                    "shutdown_hint": adapter.shutdown_hint(dev),
                    "can_slim": can_slim,
                    "slim_note": slim_note,
                }
            )

        meta = {
            "available": True,
            "reason": "ok",
            "booted_count": booted_count,
            "installed_count": len(devices),
            "cap": cap_for(cfg, plat),
            "pool_count": len(pool_list),
            "can_slim": can_slim,
            "slim_note": slim_note,
        }
        return meta, rows

    with ThreadPoolExecutor(max_workers=3) as executor:
        ios_future = executor.submit(_collect_platform, "ios")
        android_future = executor.submit(_collect_platform, "android")
        mem_future = executor.submit(free_pct_fn)

        ios_meta, ios_rows = ios_future.result()
        android_meta, android_rows = android_future.result()
        free_pct = mem_future.result()

    all_rows = [*ios_rows, *android_rows]
    all_rows.sort(
        key=lambda row: (
            0 if row["state"] == "Booted" else 1,
            0 if row["in_pool"] else 1,
            0 if row["platform"] == "ios" else 1,
            str(row["name"]).lower(),
            str(row["device_id"]),
        )
    )

    counts = {
        "ios": int(ios_meta["booted_count"]),
        "android": int(android_meta["booted_count"]),
    }
    total_booted = counts["ios"] + counts["android"]
    total_ram_bytes = sum(
        int(row["ram_bytes"]) for row in all_rows if row["state"] == "Booted"
    )

    return {
        "timestamp": time.time(),
        "counts": counts,
        "total_booted": total_booted,
        "total_ram_bytes": total_ram_bytes,
        "caps": {
            "ios": cfg.ios_cap,
            "android": cfg.android_cap,
            "total": cfg.total_cap,
        },
        "free_memory_pct": free_pct,
        "min_free_pct": cfg.min_free_pct,
        "platforms": {
            "ios": ios_meta,
            "android": android_meta,
        },
        "pools": pools,
        "devices": all_rows,
        "config": {
            "config_dir": str(cfg.config_dir),
            "pool_file": str(cfg.pool_file),
            "default_ttl_sec": cfg.default_ttl_sec,
            "app_id": cfg.app_id,
            "owner_label": cfg.owner_label,
            "simslim_except": cfg.simslim_except,
            "android_flags": list(cfg.android_flags),
        },
    }


def check_preflight(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
    *,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> tuple[bool, list[str], dict[str, object]]:
    report = collect_audit(
        cfg,
        adapters,
        "all",
        free_pct_fn,
        match_workspace=match_workspace,
        self_owners=self_owners,
    )
    reasons: list[str] = []
    unavailable = report["unavailable"]
    assert isinstance(unavailable, dict)
    if platform in unavailable:
        reasons.append(f"{platform} backend unavailable: {unavailable[platform]}")

    counts = report["counts"]
    assert isinstance(counts, dict)
    total_booted = int(report["total_booted"])  # type: ignore[arg-type]
    plat_booted = int(counts.get(platform, 0))
    plat_cap = cap_for(cfg, platform)

    if total_booted >= cfg.total_cap:
        reasons.append(
            f"total cap reached ({total_booted}/{cfg.total_cap} booted across iOS + Android)"
        )
    if plat_booted >= plat_cap:
        reasons.append(f"{platform} cap reached ({plat_booted}/{plat_cap} booted)")

    free_pct = report["free_memory_pct"]
    if isinstance(free_pct, int) and free_pct < cfg.min_free_pct:
        reasons.append(
            f"Mac free memory {free_pct}% is below floor {cfg.min_free_pct}%"
        )

    return len(reasons) == 0, reasons, report


def init_pools(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    count: int | None,
    *,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> ServiceResult:
    prune_expired_claims(cfg)
    updated: dict[str, list[str]] = {}
    messages: list[str] = []

    def _emit(line: str) -> None:
        messages.append(line)
        if on_log is not None:
            on_log(line)

    for plat in platforms_for(platform_sel):
        adapter = adapters[plat]
        ok, reason = adapter.is_available()
        if not ok:
            _emit(f"[{plat}] skipped: {reason}")
            continue
        target_n = count if count is not None else cap_for(cfg, plat)
        excluded: set[str] = set()
        for dev in adapter.list_available():
            if dev.state == "Booted":
                excluded.add(dev.device_id)
                continue
            owner = resolve_device_owner(
                cfg,
                adapter,
                dev.device_id,
                check_app=False,
                match_workspace=match_workspace,
                self_owners=self_owners,
            )
            if owner is not None:
                excluded.add(dev.device_id)
        picks = adapter.select_pool(target_n, owned_ids=excluded)
        if not picks:
            _emit(f"[{plat}] no free devices found to add to pool.")
            continue
        for device_id in picks:
            _emit(f"[{plat}] preparing pool device {device_id}...")
            adapter.prepare_pool_device(device_id)
        updated[plat] = picks
        _emit(f"[{plat}] pool saved ({len(picks)}): {', '.join(picks)}")

    if updated:
        try:
            with state_lock(cfg.config_dir):
                pools = load_pools(cfg)
                for plat, picks in updated.items():
                    pools[plat] = picks
                save_pools(cfg, pools)
        except LockTimeoutError as exc:
            return ServiceResult(ok=False, exit_code=1, message=str(exc))
        _emit(f"Pool config: {cfg.pool_file}")
        return ServiceResult(
            ok=True,
            exit_code=0,
            message="\n".join(messages),
            data={"pools": pools, "updated": updated},
        )

    return ServiceResult(
        ok=False,
        exit_code=1,
        message="\n".join(messages) or "No pool devices updated.",
        data={"updated": {}},
    )


def set_pool_membership(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    device_or_runtime_id: str,
    in_pool: bool,
    *,
    prepare: bool = True,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> ServiceResult:
    adapter = adapters.get(platform)
    if adapter is None:
        return ServiceResult(
            ok=False, exit_code=2, message=f"Unknown platform: {platform}"
        )
    ok, reason = adapter.is_available()
    if not ok:
        return ServiceResult(
            ok=False, exit_code=1, message=f"BLOCKED: {platform} unavailable ({reason})"
        )
    _, dev = find_device_by_id(
        adapters, device_or_runtime_id, preferred_platform=platform
    )
    if dev is None or dev.platform != platform:
        return ServiceResult(
            ok=False, exit_code=2, message=f"Unknown {platform} device: {device_or_runtime_id}"
        )
    canonical_id = dev.device_id
    is_booted = dev.state == "Booted"
    prepared = False

    if in_pool:
        prune_expired_claims(cfg)
        owner = resolve_device_owner(
            cfg,
            adapter,
            canonical_id,
            check_app=is_booted,
            match_workspace=match_workspace,
            self_owners=self_owners,
        )
        if owner is not None and not owner.is_self:
            return ServiceResult(
                ok=False,
                exit_code=1,
                message=(
                    f"BLOCKED: {canonical_id} is currently in use by {owner.display()}. "
                    "Wait until it is released before adding to pool."
                ),
                data={"owner": _owner_to_dict(owner), "prepared": False},
            )
        existing_pools = load_pools(cfg)
        already_in_pool = canonical_id in existing_pools.get(platform, [])
        if prepare and not is_booted and not already_in_pool:
            try:
                with acquire_lock(cfg.lock_dir):
                    adapter.prepare_pool_device(canonical_id)
                    prepared = True
            except LockTimeoutError as exc:
                return ServiceResult(ok=False, exit_code=1, message=str(exc))

    try:
        with state_lock(cfg.config_dir):
            pools = load_pools(cfg)
            current = list(pools.get(platform, []))
            if in_pool:
                if canonical_id not in current:
                    current.append(canonical_id)
            else:
                current = [item for item in current if item != canonical_id]
            pools[platform] = current
            save_pools(cfg, pools)
    except LockTimeoutError as exc:
        return ServiceResult(ok=False, exit_code=1, message=str(exc))

    verb = "Added" if in_pool else "Removed"
    prep = "to" if in_pool else "from"
    return ServiceResult(
        ok=True,
        exit_code=0,
        message=f"{verb} {canonical_id} {prep} {platform} pool.",
        data={
            "platform": platform,
            "device_id": canonical_id,
            "in_pool": in_pool,
            "prepared": prepared,
            "pools": pools,
        },
    )


def acquire_device(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    ttl_sec: int | None,
    owner: str | None,
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
    *,
    device_id: str | None = None,
    allow_non_pool: bool = False,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
    claim_workspace: str | None = None,
    on_log: Callable[[str], None] | None = None,
) -> ServiceResult:
    adapter = adapters.get(platform)
    if adapter is None:
        return ServiceResult(
            ok=False, exit_code=2, message=f"Unknown platform: {platform}"
        )
    ok, reason = adapter.is_available()
    if not ok:
        return ServiceResult(
            ok=False,
            exit_code=2,
            message=f"BLOCKED: {platform} backend unavailable ({reason}).",
        )

    def _emit(line: str) -> None:
        if on_log is not None:
            on_log(line)

    try:
        with acquire_lock(cfg.lock_dir):
            preflight_ok, reasons, _report = check_preflight(
                cfg,
                adapters,
                platform,
                free_pct_fn,
                match_workspace=match_workspace,
                self_owners=self_owners,
            )
            if not preflight_ok:
                return ServiceResult(
                    ok=False,
                    exit_code=1,
                    message="BLOCKED: " + "; ".join(reasons),
                    data={"reasons": reasons},
                )

            pools = load_pools(cfg)
            pool_ids = pools.get(platform, [])
            booted_ids = {d.device_id for d in adapter.list_booted()}

            if device_id is not None:
                available = {d.device_id: d for d in adapter.list_available()}
                target_dev = available.get(device_id)
                if target_dev is None:
                    return ServiceResult(
                        ok=False,
                        exit_code=2,
                        message=f"Unknown {platform} device: {device_id}",
                    )
                if target_dev.device_id in booted_ids or target_dev.state == "Booted":
                    return ServiceResult(
                        ok=False,
                        exit_code=1,
                        message=f"BLOCKED: {target_dev.device_id} is already booted.",
                    )
                in_pool = target_dev.device_id in set(pool_ids)
                if not in_pool and not allow_non_pool:
                    return ServiceResult(
                        ok=False,
                        exit_code=1,
                        message=(
                            f"BLOCKED: {target_dev.device_id} is not in the {platform} pool. "
                            "Add it to the pool first or confirm non-pool boot."
                        ),
                        data={"requires_non_pool_confirm": True},
                    )
                existing_owner = resolve_device_owner(
                    cfg,
                    adapter,
                    target_dev.device_id,
                    check_app=False,
                    match_workspace=match_workspace,
                    self_owners=self_owners,
                )
                if existing_owner is not None and not existing_owner.is_self:
                    return ServiceResult(
                        ok=False,
                        exit_code=1,
                        message=(
                            f"BLOCKED: {target_dev.device_id} is owned by "
                            f"{existing_owner.display()}."
                        ),
                        data={"owner": _owner_to_dict(existing_owner)},
                    )
                if not in_pool:
                    _emit(f"Preparing non-pool {platform} device {target_dev.device_id}...")
                    adapter.prepare_pool_device(target_dev.device_id)
                _emit(f"Booting {platform} device {target_dev.device_id}...")
                target_id = adapter.boot_and_slim(target_dev.device_id)
                with state_lock(cfg.config_dir):
                    record = write_claim(
                        cfg,
                        device_id=target_dev.device_id,
                        platform=platform,
                        owner=owner,
                        ttl_sec=ttl_sec,
                        workspace=claim_workspace,
                    )
                return ServiceResult(
                    ok=True,
                    exit_code=0,
                    message=(
                        f"CLAIMED {target_dev.device_id} by {record.owner} "
                        f"(ttl {record.ttl_sec}s)\nACQUIRED {target_id}"
                    ),
                    data={
                        "platform": platform,
                        "device_id": target_dev.device_id,
                        "target_id": target_id,
                        "owner": record.owner,
                        "ttl_sec": record.ttl_sec,
                        "in_pool": in_pool,
                    },
                )

            if not pool_ids:
                return ServiceResult(
                    ok=False,
                    exit_code=1,
                    message=(
                        f"No {platform} pool yet. "
                        f"Run: mobpool init --platform {platform}"
                    ),
                )

            skipped: list[str] = []
            for candidate_id in pool_ids:
                if candidate_id in booted_ids:
                    continue
                existing_owner = resolve_device_owner(
                    cfg,
                    adapter,
                    candidate_id,
                    check_app=False,
                    match_workspace=match_workspace,
                    self_owners=self_owners,
                )
                if existing_owner is not None:
                    _emit(f"SKIP {candidate_id}: owned by {existing_owner.display()}.")
                    skipped.append(candidate_id)
                    continue

                _emit(f"Booting {platform} pool device {candidate_id}...")
                target_id = adapter.boot_and_slim(candidate_id)
                with state_lock(cfg.config_dir):
                    record = write_claim(
                        cfg,
                        device_id=candidate_id,
                        platform=platform,
                        owner=owner,
                        ttl_sec=ttl_sec,
                        workspace=claim_workspace,
                    )
                return ServiceResult(
                    ok=True,
                    exit_code=0,
                    message=(
                        f"CLAIMED {candidate_id} by {record.owner} "
                        f"(ttl {record.ttl_sec}s)\nACQUIRED {target_id}"
                    ),
                    data={
                        "platform": platform,
                        "device_id": candidate_id,
                        "target_id": target_id,
                        "owner": record.owner,
                        "ttl_sec": record.ttl_sec,
                        "in_pool": True,
                    },
                )

            if skipped:
                return ServiceResult(
                    ok=False,
                    exit_code=1,
                    message=(
                        "BLOCKED: every free pool device is owned by another session "
                        f"({', '.join(skipped)})."
                    ),
                )
            return ServiceResult(
                ok=False,
                exit_code=1,
                message=(
                    f"BLOCKED: every {platform} pool device is already booted. "
                    "Reuse one you own, or wait."
                ),
            )
    except LockTimeoutError as exc:
        return ServiceResult(ok=False, exit_code=1, message=str(exc))
    except RuntimeError as exc:
        return ServiceResult(ok=False, exit_code=1, message=f"ERROR: {exc}")


def renew_device(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    ttl_sec: int | None,
) -> ServiceResult:
    _adapter, dev = find_device_by_id(adapters, device_or_runtime_id)
    canonical_id = dev.device_id if dev else device_or_runtime_id
    try:
        with state_lock(cfg.config_dir):
            record = renew_claim(cfg, canonical_id, ttl_sec=ttl_sec)
    except LockTimeoutError as exc:
        return ServiceResult(ok=False, exit_code=1, message=str(exc))
    if record is None:
        return ServiceResult(
            ok=False,
            exit_code=1,
            message=f"No active claim found for {canonical_id}.",
        )
    remaining = record.remaining_sec()
    return ServiceResult(
        ok=True,
        exit_code=0,
        message=(
            f"RENEWED {record.device_id} by {record.owner} "
            f"(ttl {record.ttl_sec}s, {remaining}s left)"
        ),
        data={
            "device_id": record.device_id,
            "owner": record.owner,
            "ttl_sec": record.ttl_sec,
            "remaining_sec": remaining,
        },
    )


def release_device(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    keep_apps: bool,
    force: bool,
    *,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> ServiceResult:
    adapter, dev = find_device_by_id(adapters, device_or_runtime_id)
    if adapter is None:
        return ServiceResult(
            ok=False, exit_code=2, message=f"Unknown device: {device_or_runtime_id}"
        )
    canonical_id = dev.device_id if dev else device_or_runtime_id
    force_env = os.environ.get("MOBPOOL_FORCE_RELEASE", "0") == "1"
    owner = resolve_device_owner(
        cfg,
        adapter,
        canonical_id,
        check_app=True,
        match_workspace=match_workspace,
        self_owners=self_owners,
    )
    if owner is not None and not owner.is_self and not (force or force_env):
        return ServiceResult(
            ok=False,
            exit_code=1,
            message=(
                f"BLOCKED: {canonical_id} is owned by {owner.display()}. "
                "Let that session release it (or pass --force)."
            ),
            data={"requires_force": True, "owner": _owner_to_dict(owner)},
        )

    ok = adapter.release_device(canonical_id, keep_apps=keep_apps)
    if not ok:
        return ServiceResult(
            ok=False,
            exit_code=1,
            message=f"ERROR: failed to shut down {canonical_id}.",
        )
    try:
        with state_lock(cfg.config_dir):
            remove_claim(cfg, canonical_id)
    except LockTimeoutError:
        remove_claim(cfg, canonical_id)
    return ServiceResult(
        ok=True,
        exit_code=0,
        message=f"RELEASED {canonical_id}",
        data={"device_id": canonical_id, "keep_apps": keep_apps},
    )


def slim_device(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    platform: str | None = None,
    *,
    force: bool = False,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> ServiceResult:
    adapter, dev = find_device_by_id(
        adapters, device_or_runtime_id, preferred_platform=platform
    )
    if adapter is None:
        return ServiceResult(
            ok=False, exit_code=2, message=f"Unknown device: {device_or_runtime_id}"
        )
    canonical_id = dev.device_id if dev else device_or_runtime_id
    is_booted = dev is not None and dev.state == "Booted"
    force_env = os.environ.get("MOBPOOL_FORCE_RELEASE", "0") == "1"
    owner = resolve_device_owner(
        cfg,
        adapter,
        canonical_id,
        check_app=is_booted,
        match_workspace=match_workspace,
        self_owners=self_owners,
    )
    if owner is not None and not owner.is_self and not (force or force_env):
        return ServiceResult(
            ok=False,
            exit_code=1,
            message=(
                f"BLOCKED: {canonical_id} is owned by {owner.display()}. "
                "Slimming may boot or reboot the device (pass --force to override)."
            ),
            data={"requires_force": True, "owner": _owner_to_dict(owner)},
        )
    try:
        output = adapter.slim_device(canonical_id)
        return ServiceResult(
            ok=True,
            exit_code=0,
            message=output,
            data={"device_id": canonical_id, "platform": adapter.platform},
        )
    except RuntimeError as exc:
        return ServiceResult(ok=False, exit_code=1, message=f"ERROR: {exc}")
