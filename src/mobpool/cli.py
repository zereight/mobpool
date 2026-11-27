"""Unified CLI for mobpool (iOS simulators + Android emulators)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, Sequence

from mobpool.claims import prune_expired_claims
from mobpool.config import MobpoolConfig, load_config
from mobpool.gui import serve_gui
from mobpool.memory import mac_free_memory_pct
from mobpool.platforms.base import PlatformAdapter
from mobpool.service import (
    acquire_device,
    check_preflight,
    collect_audit,
    default_adapters,
    init_pools,
    platforms_for,
    release_device,
    renew_device,
    resolve_device_owner,
    slim_device,
)


def cmd_init(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    count: int | None,
) -> int:
    result = init_pools(cfg, adapters, platform_sel, count, on_log=print)
    if not result.ok and result.message and not result.data.get("updated"):
        pass
    return result.exit_code


def cmd_audit(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
    as_json: bool,
    free_pct_fn: Callable[[], int | None],
) -> int:
    report = collect_audit(cfg, adapters, platform_sel, free_pct_fn)
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
    for plat in platforms_for(platform_sel):
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
    ok, reasons, _report = check_preflight(cfg, adapters, platform, free_pct_fn)
    if ok:
        print(f"OK to boot one more {platform} device.")
    else:
        print("BLOCKED: " + "; ".join(reasons))
    return 0 if ok else 1


def cmd_acquire(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform: str,
    ttl_sec: int | None,
    owner: str | None,
    free_pct_fn: Callable[[], int | None],
) -> int:
    def _log(line: str) -> None:
        if line.startswith("SKIP "):
            print(line, file=sys.stderr)
        else:
            print(line)

    result = acquire_device(
        cfg,
        adapters,
        platform=platform,
        ttl_sec=ttl_sec,
        owner=owner,
        free_pct_fn=free_pct_fn,
        on_log=_log,
    )
    if result.message:
        print(result.message)
    return result.exit_code


def cmd_renew(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    ttl_sec: int | None,
) -> int:
    result = renew_device(cfg, adapters, device_or_runtime_id, ttl_sec)
    if result.message:
        print(result.message)
    return result.exit_code


def cmd_release(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    device_or_runtime_id: str,
    keep_apps: bool,
    force: bool,
) -> int:
    result = release_device(cfg, adapters, device_or_runtime_id, keep_apps, force)
    if result.message:
        print(result.message)
    return result.exit_code


def cmd_owners(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    platform_sel: str,
) -> int:
    prune_expired_claims(cfg)
    found_any = False
    for plat in platforms_for(platform_sel):
        adapter = adapters[plat]
        ok, _ = adapter.is_available()
        if not ok:
            continue
        for dev in adapter.list_available():
            owner = resolve_device_owner(
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
    force: bool = False,
) -> int:
    result = slim_device(
        cfg, adapters, device_or_runtime_id, platform=platform, force=force
    )
    if result.message:
        print(result.message)
    return result.exit_code


def cmd_gui(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter],
    host: str,
    port: int,
    no_open: bool,
    free_pct_fn: Callable[[], int | None],
) -> int:
    return serve_gui(
        cfg,
        adapters=adapters,
        free_pct_fn=free_pct_fn,
        host=host,
        port=port,
        open_browser=not no_open,
    )


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
    p_slim.add_argument(
        "--force",
        action="store_true",
        help="Bypass ownership protection when slimming a booted device.",
    )

    p_gui = sub.add_parser(
        "gui", help="Launch local web dashboard to manage iOS & Android together."
    )
    p_gui.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback bind host (127.0.0.1, localhost, or ::1).",
    )
    p_gui.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Local HTTP port (use 0 for an automatic free port).",
    )
    p_gui.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the dashboard URL in a browser.",
    )

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
    resolved_adapters = adapters or default_adapters(config)

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
        return cmd_slim(
            config, resolved_adapters, args.device_id, args.platform, args.force
        )
    if command == "gui":
        return cmd_gui(
            config,
            resolved_adapters,
            args.host,
            args.port,
            args.no_open,
            free_pct_fn,
        )
    parser.print_help()
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
