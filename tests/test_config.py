import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from mobpool.config import load_config


class TestConfig(unittest.TestCase):
    def test_loads_local_config_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp)
            (cfg_dir / "config.json").write_text(
                json.dumps(
                    {
                        "app_id": "com.example.dev",
                        "worktree_claims_dir": "~/claims/worktrees",
                        "ios_cap": 3,
                        "default_ttl_sec": 7200,
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"MOBPOOL_CONFIG_DIR": str(cfg_dir)},
                clear=True,
            ):
                cfg = load_config()
            self.assertEqual(cfg.app_id, "com.example.dev")
            self.assertEqual(cfg.rb_claims_dir, Path("~/claims/worktrees").expanduser())
            self.assertEqual(cfg.ios_cap, 3)
            self.assertEqual(cfg.default_ttl_sec, 7200)

    def test_env_overrides_local_config_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp)
            (cfg_dir / "config.json").write_text(
                json.dumps(
                    {
                        "app_id": "com.example.file",
                        "worktree_claims_dir": "/tmp/file-claims",
                        "ios_cap": 3,
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {
                    "MOBPOOL_CONFIG_DIR": str(cfg_dir),
                    "MOBPOOL_APP_ID": "com.example.env",
                    "MOBPOOL_WORKTREE_CLAIMS_DIR": "/tmp/env-claims",
                    "MOBPOOL_IOS_CAP": "1",
                },
                clear=True,
            ):
                cfg = load_config()
            self.assertEqual(cfg.app_id, "com.example.env")
            self.assertEqual(cfg.rb_claims_dir, Path("/tmp/env-claims"))
            self.assertEqual(cfg.ios_cap, 1)


if __name__ == "__main__":
    unittest.main()
