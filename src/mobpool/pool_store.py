"""Persistent pool configuration for iOS and Android devices."""

from __future__ import annotations

import json
import os
from pathlib import Path

from mobpool.config import MobpoolConfig


def _read_legacy_sim_guard_pool(path: Path) -> list[str]:
    if not path.is_file():
        return []
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        cleaned = raw.split("#", 1)[0].strip()
        if cleaned and cleaned not in entries:
            entries.append(cleaned)
    return entries


def load_pools(cfg: MobpoolConfig) -> dict[str, list[str]]:
    pools: dict[str, list[str]] = {"ios": [], "android": []}
    if cfg.pool_file.is_file():
        try:
            data = json.loads(cfg.pool_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key in ("ios", "android"):
                    values = data.get(key)
                    if isinstance(values, list):
                        pools[key] = [str(item) for item in values if str(item).strip()]
        except Exception:
            pass
    if not pools["ios"]:
        legacy = _read_legacy_sim_guard_pool(cfg.legacy_sg_pool_file)
        if legacy:
            pools["ios"] = legacy
    return pools


def save_pools(cfg: MobpoolConfig, pools: dict[str, list[str]]) -> None:
    cfg.pool_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ios": list(dict.fromkeys(pools.get("ios", []))),
        "android": list(dict.fromkeys(pools.get("android", []))),
    }
    tmp = cfg.pool_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, cfg.pool_file)
