"""Unified CLI for mobpool (iOS simulators + Android emulators)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable, Sequence

from mobpool.claims import (
    OwnerInfo,
    prune_expired_claims,
    remove_claim,
    renew_claim,
    resolve_owner,
    write_claim,
)
from mobpool.config import MobpoolConfig, load_config
from mobpool.lock import LockTimeoutError, acquire_lock
from mobpool.memory import mac_free_memory_pct
from mobpool.platforms.android import AndroidAdapter
from mobpool.platforms.base import DeviceInfo, PlatformAdapter
from mobpool.platforms.ios import IOSAdapter
from mobpool.pool_store import load_pools, save_pools


def _default_adapters(cfg: MobpoolConfig) -> dict[str, PlatformAdapter]:
    return {
        "ios": IOSAdapter(cfg),
        "android": AndroidAdapter(cfg),
    }


def _platforms_for(selection: str) -> list[str]:
    if selection == "all":
        return ["ios", "android"]
    return [selection]


def _cap_for(cfg: MobpoolConfig, platform: str) -> int:
    return cfg.ios_cap if platform == "ios" else cfg.android_cap


def _resolve_device_owner(
    cfg: MobpoolConfig,
    adapter: PlatformAdapter,
    device_id: str,
    check_app: bool = True,
) -> OwnerInfo | None:
    app_fn = adapter.is_app_running if check_app else None
    return resolve_owner(cfg, device_id, app_running_fn=app_fn)


def _find_device_by_id(
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


def cmd_init(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    count: int | None,
) -> int:
    pools = load_pools(cfg)
    prune_expired_claims(cfg)
    changed = False

    for plat in _platforms_for(platform_sel):
        adapter = adapters[plat]
        ok, reason = adapter.is_available()
        if not ok:
            print(f"[{plat}] skipped: {reason}")
            continue
        target_n = count if count is not None else _cap_for(cfg, plat)
        owned: set[str] = set()
        for dev in adapter.list_available():
            owner = _resolve_device_owner(
                cfg, adapter, dev.device_id, check_app=(dev.state == "Booted")
            )
            if owner is not None:
                owned.add(dev.device_id)
        picks = adapter.select_pool(target_n, owned_ids=owned)
        if not picks:
            print(f"[{plat}] no free devices found to add to pool.")
            continue
        for device_id in picks:
            print(f"[{plat}] preparing pool device {device_id}...")
            adapter.prepare_pool_device(device_id)
        pools[plat] = picks
        changed = True
        print(f"[{plat}] pool saved ({len(picks)}): {', '.join(picks)}")

    if changed:
        save_pools(cfg, pools)
        print(f"Pool config: {cfg.pool_file}")
        return 0
    return 1


def _collect_audit(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    free_pct_fn: Callable[[], int | None],
) -> dict[str, object]:
    prune_expired_claims(cfg)
    pools = load_pools(cfg)
    rows: list[dict[str, object]] = []
    counts: dict[str, int] = {"ios": 0, "android": 0}
    unavailable: dict[str, str] = {}

    for plat in _platforms_for(platform_sel):
        adapter = adapters[plat]
        ok, reason = adapter.is_available()
        if not ok:
            unavailable[plat] = reason
            continue
        booted = adapter.list_booted()
        counts[plat] = len(booted)
        pool_set = set(pools.get(plat, []))
        for dev in booted:
            owner = _resolve_device_owner(cfg, adapter, dev.device_id, check_app=True)
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


def cmd_audit(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    as_json: bool,
    free_pct_fn: Callable[[], int | None],
) -> int:
    report = _collect_audit(cfg, adapters, platform_sel, free_pct_fn)
    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    rows = report["devices"]
    assert isinstance(rows, list)
    total_ram = sum(int(item["ram_bytes"]) for item in rows)
    counts = report["counts"]
    assert isinstance(counts, dict)
    print(
        f"Booted devices: {report['total_booted']}/{cfg.total_cap} "
        f"(iOS {counts['ios']}/{cfg.ios_cap}, Android {counts['android']}/{cfg.android_cap}), "
        f"total RAM {total_ram / 1e9:.2f} GB"
    )

    unavailable = report["unavailable"]
    assert isinstance(unavailable, dict)
    for plat, reason in unavailable.items():
        print(f"  [{plat}] unavailable: {reason}")

    pools = report["pools"]
    assert isinstance(pools, dict)
    for plat in _platforms_for(platform_sel):
        if plat not in unavailable and not pools.get(plat):
            print(f"  [{plat}] no pool yet. Run: mobpool init --platform {plat}")

    orphans: list[dict[str, object]] = []
    for item in rows:
        ram_gb = int(item["ram_bytes"]) / 1e9
        target_note = (
            f" ({item['target_id']})"
            if item["target_id"] != item["device_id"]
            else ""
        )
        print(
            f"  [{item['platform']:<7}] {item['device_id']}{target_note}  "
            f"{str(item['name']):<18} {str(item['os_version']):<11} "
            f"{ram_gb:5.2f} GB  cpu {float(item['cpu_pct']):4.1f}%  "
            f"{item['slim_status']}  [{item['tag']}]"
        )
        if item["is_orphan"]:
            orphans.append(item)

    if orphans:
        print("Orphans (not in pool, not claimed). Verify no live agent uses them, then:")
        for item in orphans:
            print(f"  {item['shutdown_hint']}")

    free_pct = report["free_memory_pct"]
    free_label = f"{free_pct}%" if free_pct is not None else "unknown"
    print(f"Mac memory free: {free_label} (floor {cfg.min_free_pct}%)")
    return 0


def _check_preflight(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    free_pct_fn: Callable[[], int | None],
) -> tuple[bool, str]:
    report = _collect_audit(cfg, adapters, "all", free_pct_fn)
    counts = report["counts"]
    assert isinstance(counts, dict)
    total_booted = int(report["total_booted"])
    plat_booted = int(counts.get(platform, 0))
    plat_cap = _cap_for(cfg, platform)

    if plat_booted >= plat_cap:
        return (
            False,
            f"BLOCKED: {plat_booted} {platform} device(s) booted, cap is {plat_cap}. "
            "Reuse one you own, wait, or shut down an orphan.",
        )
    if total_booted >= cfg.total_cap:
        return (
            False,
            f"BLOCKED: {total_booted} total devices booted, machine cap is {cfg.total_cap}.",
        )
    free_pct = report["free_memory_pct"]
    if isinstance(free_pct, int) and free_pct < cfg.min_free_pct:
        return (
            False,
            f"BLOCKED: only {free_pct}% memory free (floor {cfg.min_free_pct}%).",
        )
    return True, f"OK to boot one more {platform} device."


def cmd_preflight(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    free_pct_fn: Callable[[], int | None],
) -> int:
    cmd_audit(cfg, adapters, "all", as_json=False, free_pct_fn=free_pct_fn)
    ok, msg = _check_preflight(cfg, adapters, platform, free_pct_fn)
    print(msg)
    return 0 if ok else 1


def cmd_acquire(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    ttl_sec: int | None,
    owner: str | None,
    free_pct_fn: Callable[[], int | None],
) -> int:
    adapter = adapters[platform]
    ok, reason = adapter.is_available()
    if not ok:
        print(f"BLOCKED: {platform} backend unavailable ({reason}).")
        return 2

    pools = load_pools(cfg)
    pool_ids = pools.get(platform, [])
    if not pool_ids:
        print(f"No {platform} pool yet. Run: mobpool init --platform {platform}")
        return 1

    try:
        lock_ctx = acquire_lock(cfg.lock_dir)
        with lock_ctx:
            prune_expired_claims(cfg)
            can_boot, msg = _check_preflight(cfg, adapters, platform, free_pct_fn)
            if not can_boot:
                print(msg)
                return 1

            booted_ids = {dev.device_id for dev in adapter.list_booted()}
            skipped: list[str] = []
            for device_id in pool_ids:
                if device_id in booted_ids:
                    continue
                existing_owner = _resolve_device_owner(
                    cfg, adapter, device_id, check_app=False
                )
                if existing_owner is not None:
                    print(
                        f"SKIP {device_id}: owned by {existing_owner.display()}.",
                        file=sys.stderr,
                    )
                    skipped.append(device_id)
                    continue

                print(f"Booting {platform} pool device {device_id}...")
                target_id = adapter.boot_and_slim(device_id)
                record = write_claim(
                    cfg,
                    device_id=device_id,
                    platform=platform,
                    owner=owner,
                    ttl_sec=ttl_sec,
                )
                print(
                    f"CLAIMED {device_id} by {record.owner} "
                    f"(ttl {record.ttl_sec}s)"
                )
                print(f"ACQUIRED {target_id}")
                return 0

            if skipped:
                print(
                    "BLOCKED: every free pool device is owned by another session "
                    f"({', '.join(skipped)})."
                )
            else:
                print(
                    f"BLOCKED: every {platform} pool device is already booted. "
                    "Reuse one you own, or wait."
                )
            return 1
    except LockTimeoutError as exc:
        print(str(exc))
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1


def cmd_renew(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    ttl_sec: int | None,
) -> int:
    _adapter, dev = _find_device_by_id(adapters, device_or_runtime_id)
    canonical_id = dev.device_id if dev else device_or_runtime_id
    record = renew_claim(cfg, canonical_id, ttl_sec=ttl_sec)
    if record is None:
        print(f"No active claim found for {canonical_id}.")
        return 1
    print(
        f"RENEWED {record.device_id} by {record.owner} "
        f"(ttl {record.ttl_sec}s, {record.remaining_sec()}s left)"
    )
    return 0


def cmd_release(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    keep_apps: bool,
    force: bool,
) -> int:
    adapter, dev = _find_device_by_id(adapters, device_or_runtime_id)
    if adapter is None:
        print(f"Unknown device: {device_or_runtime_id}")
        return 2
    canonical_id = dev.device_id if dev else device_or_runtime_id
    force_env = os.environ.get("MOBPOOL_FORCE_RELEASE", "0") == "1"
    owner = _resolve_device_owner(cfg, adapter, canonical_id, check_app=True)
    if owner is not None and not owner.is_self and not (force or force_env):
        print(
            f"BLOCKED: {canonical_id} is owned by {owner.display()}. "
            "Let that session release it (or pass --force)."
        )
        return 1

    ok = adapter.release_device(canonical_id, keep_apps=keep_apps)
    if not ok:
        print(f"ERROR: failed to shut down {canonical_id}.")
        return 1
    remove_claim(cfg, canonical_id)
    print(f"RELEASED {canonical_id}")
    return 0


def cmd_owners(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
) -> int:
    prune_expired_claims(cfg)
    found_any = False
    for plat in _platforms_for(platform_sel):
        adapter = adapters[plat]
        ok, _ = adapter.is_available()
        if not ok:
            continue
        for dev in adapter.list_available():
            owner = _resolve_device_owner(
                cfg, adapter, dev.device_id, check_app=(dev.state == "Booted")
            )
            if owner is not None:
                found_any = True
                print(f"{plat}\t{dev.device_id}\t{owner.display()}")
    if not found_any:
        print("No claimed devices.")
    return 0


def cmd_slim(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    platform: str | None,
) -> int:
    adapter, dev = _find_device_by_id(
        adapters, device_or_runtime_id, preferred_platform=platform
    )
    if adapter is None:
        print(f"Unknown device: {device_or_runtime_id}")
        return 2
    canonical_id = dev.device_id if dev else device_or_runtime_id
    try:
        output = adapter.slim_device(canonical_id)
        print(output)
        return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mobpool",
        description="Unified iOS simulator & Android emulator pool, lease, and slimming manager.",
    )
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Select and prepare pool devices.")
    p_init.add_argument(
        "--platform", choices=("ios", "android", "all"), default="all"
    )
    p_init.add_argument("--count", type=int, default=None)

    p_audit = sub.add_parser("audit", help="Show booted devices, RAM/CPU, slim status, and owners.")
    p_audit.add_argument(
        "--platform", choices=("ios", "android", "all"), default="all"
    )
    p_audit.add_argument("--json", action="store_true", dest="as_json")

    p_pre = sub.add_parser("preflight", help="Audit and check caps + free memory before booting.")
    p_pre.add_argument("--platform", choices=("ios", "android"), default="ios")

    p_acq = sub.add_parser("acquire", help="Boot a free pool device (slim) and write a TTL lease.")
    p_acq.add_argument("--platform", choices=("ios", "android"), default="ios")
    p_acq.add_argument("--ttl", type=int, default=None, help="Lease TTL in seconds.")
    p_acq.add_argument("--owner", type=str, default=None, help="Owner label for this lease.")

    p_ren = sub.add_parser("renew", help="Extend an active TTL lease (heartbeat).")
    p_ren.add_argument("device_id")
    p_ren.add_argument("--ttl", type=int, default=None)

    p_rel = sub.add_parser("release", help="Clean apps, shut down device, and drop its lease.")
    p_rel.add_argument("device_id")
    p_rel.add_argument("--keep-apps", action="store_true")
    p_rel.add_argument("--force", action="store_true")

    p_own = sub.add_parser("owners", help="List claimed devices and their owners.")
    p_own.add_argument(
        "--platform", choices=("ios", "android", "all"), default="all"
    )

    p_slim = sub.add_parser("slim", help="Apply slimming profile to a device.")
    p_slim.add_argument("device_id")
    p_slim.add_argument("--platform", choices=("ios", "android"), default=None)

    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    cfg: MobpoolConfig | None = None,
    adapters: dict[str, PlatformAdapter] | None = None,
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    config = cfg or load_config()
    resolved_adapters = adapters or _default_adapters(config)

    command = args.command or "audit"
    if command == "init":
        return cmd_init(config, resolved_adapters, args.platform, args.count)
    if command == "audit":
        as_json = getattr(args, "as_json", False)
        platform = getattr(args, "platform", "all")
        return cmd_audit(config, resolved_adapters, platform, as_json, free_pct_fn)
    if command == "preflight":
        return cmd_preflight(config, resolved_adapters, args.platform, free_pct_fn)
    if command == "acquire":
        return cmd_acquire(
            config, resolved_adapters, args.platform, args.ttl, args.owner, free_pct_fn
        )
    if command == "renew":
        return cmd_renew(config, resolved_adapters, args.device_id, args.ttl)
    if command == "release":
        return cmd_release(
            config, resolved_adapters, args.device_id, args.keep_apps, args.force
        )
    if command == "owners":
        return cmd_owners(config, resolved_adapters, args.platform)
    if command == "slim":
        return cmd_slim(config, resolved_adapters, args.device_id, args.platform)
    parser.print_help()
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
