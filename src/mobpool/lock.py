"""Atomic directory-based lock with stale-lock recovery."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Iterator
import uuid


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


def _write_lock_meta(lock_dir: Path, payload: dict[str, object]) -> None:
    raw = json.dumps(payload)
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=lock_dir,
            prefix=".meta.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            tmp_path = fh.name
            fh.write(raw)
        os.replace(tmp_path, lock_dir / "meta.json")
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def _lock_token_matches(lock_dir: Path, token: str) -> bool:
    meta_file = lock_dir / "meta.json"
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return False
    return meta.get("token") == token


@contextmanager
def acquire_lock(
    lock_dir: Path,
    timeout_sec: float = 10.0,
    poll_sec: float = 0.25,
    stale_after_sec: float = 360.0,
) -> Iterator[None]:
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_sec
    acquired = False
    token = uuid.uuid4().hex

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

    _write_lock_meta(
        lock_dir,
        {"pid": os.getpid(), "created_at": time.time(), "token": token},
    )
    try:
        yield
    finally:
        if acquired and _lock_token_matches(lock_dir, token):
            shutil.rmtree(lock_dir, ignore_errors=True)


@contextmanager
def state_lock(
    config_dir: Path,
    timeout_sec: float = 10.0,
    poll_sec: float = 0.05,
    stale_after_sec: float = 60.0,
) -> Iterator[None]:
    with acquire_lock(
        config_dir / "state.lock",
        timeout_sec=timeout_sec,
        poll_sec=poll_sec,
        stale_after_sec=stale_after_sec,
    ):
        yield
