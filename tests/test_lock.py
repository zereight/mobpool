from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mobpool.lock import LockTimeoutError, acquire_lock


class TestLock(unittest.TestCase):
    def test_acquire_and_release_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_dir = Path(tmp) / "acquire.lock"
            with acquire_lock(lock_dir):
                self.assertTrue(lock_dir.is_dir())
                with self.assertRaises(LockTimeoutError):
                    with acquire_lock(lock_dir, timeout_sec=0.1, poll_sec=0.05):
                        pass
            self.assertFalse(lock_dir.exists())

    def test_stale_dead_pid_lock_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_dir = Path(tmp) / "acquire.lock"
            lock_dir.mkdir()
            (lock_dir / "meta.json").write_text(
                json.dumps({"pid": 999999, "created_at": 1.0}),
                encoding="utf-8",
            )
            with acquire_lock(lock_dir, timeout_sec=1.0):
                self.assertTrue(lock_dir.is_dir())
            self.assertFalse(lock_dir.exists())


if __name__ == "__main__":
    unittest.main()
