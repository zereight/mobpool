"""Persistent pool configuration for iOS and Android devices."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

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
    raw = json.dumps(payload, indent=2) + "\n"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cfg.pool_file.parent,
            prefix=f".{cfg.pool_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            tmp_path = fh.name
            fh.write(raw)
        os.replace(tmp_path, cfg.pool_file)
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise
