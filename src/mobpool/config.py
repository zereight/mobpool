"""Configuration and environment defaults for mobpool."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
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
    claims_dir = Path(
        os.environ.get("MOBPOOL_CLAIMS_DIR", str(config_dir / "claims"))
    ).expanduser()
    lock_dir = Path(
        os.environ.get("MOBPOOL_LOCK_DIR", str(config_dir / "acquire.lock"))
    ).expanduser()
    pool_file = Path(
        os.environ.get("MOBPOOL_POOL_FILE", str(config_dir / "pools.json"))
    ).expanduser()

    raw_flags = os.environ.get(
        "MOBPOOL_ANDROID_FLAGS",
        "-no-audio -no-boot-anim -gpu host -no-snapshot-save",
    ).strip()
    android_flags = tuple(raw_flags.split()) if raw_flags else ()

    workspace = Path(os.environ.get("MOBPOOL_WORKSPACE") or os.getcwd()).resolve()
    owner_label = os.environ.get("MOBPOOL_OWNER", "").strip()

    raw_rb = (
        os.environ.get("MOBPOOL_WORKTREE_CLAIMS_DIR")
        or os.environ.get("RB_CLAIMS")
        or ""
    ).strip()
    return MobpoolConfig(
        config_dir=config_dir,
        claims_dir=claims_dir,
        lock_dir=lock_dir,
        pool_file=pool_file,
        ios_cap=_env_int("MOBPOOL_IOS_CAP", 2),
        android_cap=_env_int("MOBPOOL_ANDROID_CAP", 1),
        total_cap=_env_int("MOBPOOL_TOTAL_CAP", 2),
        min_free_pct=_env_int("MOBPOOL_MIN_FREE_PCT", 25),
        default_ttl_sec=_env_int("MOBPOOL_CLAIM_TTL", 3600),
        simslim_except=os.environ.get("SIMSLIM_EXCEPT", "store,web"),
        android_flags=android_flags,
        app_id=os.environ.get("MOBPOOL_APP_ID", "").strip(),
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
