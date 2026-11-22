"""Host memory availability checks (macOS memory_pressure)."""

from __future__ import annotations

import re
import subprocess


_FREE_PCT_RE = re.compile(r"free percentage:\s*(\d+)%", re.IGNORECASE)


def parse_free_pct(output: str) -> int | None:
    match = _FREE_PCT_RE.search(output)
    if not match:
        return None
    return int(match.group(1))


def mac_free_memory_pct() -> int | None:
    try:
        proc = subprocess.run(
            ["memory_pressure"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    return parse_free_pct(proc.stdout)
