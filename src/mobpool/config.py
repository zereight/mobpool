"""Configuration and environment defaults for mobpool."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


def _load_local_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_int(name: str, file_cfg: dict[str, Any], key: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            return default
    val = file_cfg.get(key)
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return int(val.strip())
        except ValueError:
            return default
    return default


def _resolve_str(name: str, file_cfg: dict[str, Any], key: str, default: str) -> str:
    raw = os.environ.get(name, "").strip()
    if raw:
        return raw
    val = file_cfg.get(key)
    if isinstance(val, str) and val.strip():
        return val.strip()
    return default


@dataclass(frozen=True)
class MobpoolConfig:
    config_dir: Path
    claims_dir: Path
    lock_dir: Path
    pool_file: Path
    ios_cap: int
    android_cap: int
    total_cap: int
    min_free_pct: int
    default_ttl_sec: int
    simslim_except: str
    android_flags: tuple[str, ...]
    app_id: str
    workspace: Path
    owner_label: str
    rb_claims_dir: Path | None
    legacy_sg_claims_dir: Path
    legacy_ad_claims_dir: Path
    legacy_sg_pool_file: Path


def load_config() -> MobpoolConfig:
    config_dir = Path(
        os.environ.get("MOBPOOL_CONFIG_DIR", "~/.config/mobpool")
    ).expanduser()
    config_file = Path(
        os.environ.get("MOBPOOL_CONFIG_FILE", str(config_dir / "config.json"))
    ).expanduser()
    file_cfg = _load_local_file(config_file)
    claims_dir = Path(
        os.environ.get("MOBPOOL_CLAIMS_DIR", str(config_dir / "claims"))
    ).expanduser()
    lock_dir = Path(
        os.environ.get("MOBPOOL_LOCK_DIR", str(config_dir / "acquire.lock"))
    ).expanduser()
    pool_file = Path(
        os.environ.get("MOBPOOL_POOL_FILE", str(config_dir / "pools.json"))
    ).expanduser()

    default_flags = "-no-audio -no-boot-anim -gpu host -no-snapshot-save"
    raw_env_flags = os.environ.get("MOBPOOL_ANDROID_FLAGS")
    if raw_env_flags is not None:
        android_flags = tuple(raw_env_flags.strip().split()) if raw_env_flags.strip() else ()
    elif isinstance(file_cfg.get("android_flags"), list):
        android_flags = tuple(str(x).strip() for x in file_cfg["android_flags"] if str(x).strip())
    elif isinstance(file_cfg.get("android_flags"), str):
        raw_file_flags = file_cfg["android_flags"].strip()
        android_flags = tuple(raw_file_flags.split()) if raw_file_flags else ()
    else:
        android_flags = tuple(default_flags.split())

    workspace = Path(os.environ.get("MOBPOOL_WORKSPACE") or os.getcwd()).resolve()
    owner_label = _resolve_str("MOBPOOL_OWNER", file_cfg, "owner_label", "")

    raw_rb = (
        os.environ.get("MOBPOOL_WORKTREE_CLAIMS_DIR")
        or os.environ.get("RB_CLAIMS")
        or (file_cfg.get("worktree_claims_dir") if isinstance(file_cfg.get("worktree_claims_dir"), str) else "")
        or ""
    ).strip()
    return MobpoolConfig(
        config_dir=config_dir,
        claims_dir=claims_dir,
        lock_dir=lock_dir,
        pool_file=pool_file,
        ios_cap=_resolve_int("MOBPOOL_IOS_CAP", file_cfg, "ios_cap", 2),
        android_cap=_resolve_int("MOBPOOL_ANDROID_CAP", file_cfg, "android_cap", 1),
        total_cap=_resolve_int("MOBPOOL_TOTAL_CAP", file_cfg, "total_cap", 2),
        min_free_pct=_resolve_int("MOBPOOL_MIN_FREE_PCT", file_cfg, "min_free_pct", 25),
        default_ttl_sec=_resolve_int("MOBPOOL_CLAIM_TTL", file_cfg, "default_ttl_sec", 3600),
        simslim_except=_resolve_str("SIMSLIM_EXCEPT", file_cfg, "simslim_except", "store,web"),
        android_flags=android_flags,
        app_id=_resolve_str("MOBPOOL_APP_ID", file_cfg, "app_id", ""),
        workspace=workspace,
        owner_label=owner_label,
        rb_claims_dir=Path(raw_rb).expanduser() if raw_rb else None,
        legacy_sg_claims_dir=Path(
            os.environ.get("SG_CLAIMS", "~/.config/sim-guard/claims")
        ).expanduser(),
        legacy_ad_claims_dir=Path(
            os.environ.get("AD_CLAIMS", "~/.agent-device/device-claims")
        ).expanduser(),
        legacy_sg_pool_file=Path(
            os.environ.get("SIM_GUARD_CONFIG", "~/.config/sim-guard/pool")
        ).expanduser(),
    )
