"""Atomic directory-based lock with stale-lock recovery."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import time
from typing import Iterator


class LockTimeoutError(RuntimeError):
    """Raised when another mobpool acquire holds the lock past the timeout."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _is_stale(lock_dir: Path, stale_after_sec: float, now: float) -> bool:
    meta_file = lock_dir / "meta.json"
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        pid = int(meta.get("pid", 0))
        created = float(meta.get("created_at", 0.0))
    except Exception:
        try:
            age = now - lock_dir.stat().st_mtime
            return age > stale_after_sec
        except OSError:
            return False
    if pid and not _pid_alive(pid):
        return True
    if created and (now - created) > stale_after_sec:
        return True
    return False


@contextmanager
def acquire_lock(
    lock_dir: Path,
    timeout_sec: float = 10.0,
    poll_sec: float = 0.25,
    stale_after_sec: float = 120.0,
) -> Iterator[None]:
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_sec
    acquired = False

    while True:
        try:
            os.mkdir(lock_dir)
            acquired = True
            break
        except FileExistsError:
            now = time.time()
            if _is_stale(lock_dir, stale_after_sec=stale_after_sec, now=now):
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            if time.monotonic() >= deadline:
                raise LockTimeoutError(
                    f"BLOCKED: another mobpool acquire is running (lock {lock_dir})."
                )
            time.sleep(poll_sec)

    meta_path = lock_dir / "meta.json"
    meta_path.write_text(
        json.dumps({"pid": os.getpid(), "created_at": time.time()}),
        encoding="utf-8",
    )
    try:
        yield
    finally:
        if acquired:
            shutil.rmtree(lock_dir, ignore_errors=True)
