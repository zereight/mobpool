from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from mobpool.claims import (
    prune_expired_claims,
    read_active_claim,
    remove_claim,
    renew_claim,
    resolve_owner,
    write_claim,
)
from mobpool.config import MobpoolConfig


def make_cfg(root: Path, owner_label: str = "task-a", workspace: Path | None = None) -> MobpoolConfig:
    return MobpoolConfig(
        config_dir=root / "config",
        claims_dir=root / "config" / "claims",
        lock_dir=root / "config" / "acquire.lock",
        pool_file=root / "config" / "pools.json",
        ios_cap=2,
        android_cap=1,
        total_cap=2,
        min_free_pct=25,
        default_ttl_sec=1800,
        simslim_except="store,web",
        android_flags=("-no-audio", "-no-boot-anim"),
        app_id="com.example.mobile.dev",
        workspace=(workspace or root / "ws-a").resolve(),
        owner_label=owner_label,
        rb_claims_dir=root / "rb-claims",
        legacy_sg_claims_dir=root / "sg-claims",
        legacy_ad_claims_dir=root / "ad-claims",
        legacy_sg_pool_file=root / "sg-pool",
    )


class TestClaims(unittest.TestCase):
    def test_ttl_claim_persists_without_pid_and_expires_after_ttl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(Path(tmp))
            rec = write_claim(cfg, "SIM-1", "ios", owner="agent-1", ttl_sec=300, now=1000.0)
            self.assertEqual(rec.expires_at, 1300.0)

            active = read_active_claim(cfg, "SIM-1", now=1200.0)
            self.assertIsNotNone(active)
            assert active is not None
            self.assertEqual(active.remaining_sec(1200.0), 100)

            expired = read_active_claim(cfg, "SIM-1", now=1301.0)
            self.assertIsNone(expired)
            self.assertEqual(prune_expired_claims(cfg, now=1301.0), 1)

    def test_renew_extends_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(Path(tmp))
            write_claim(cfg, "Pixel_9_Bot", "android", ttl_sec=600, now=2000.0)
            renewed = renew_claim(cfg, "Pixel_9_Bot", ttl_sec=1200, now=2500.0)
            self.assertIsNotNone(renewed)
            assert renewed is not None
            self.assertEqual(renewed.expires_at, 3700.0)

    def test_resolve_owner_distinguishes_self_and_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_a = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            cfg_b = make_cfg(root, owner_label="agent-b", workspace=root / "ws-b")
            write_claim(cfg_a, "SIM-2", "ios", ttl_sec=600, now=1000.0)

            owner_a = resolve_owner(cfg_a, "SIM-2", now=1050.0)
            owner_b = resolve_owner(cfg_b, "SIM-2", now=1050.0)
            self.assertIsNotNone(owner_a)
            self.assertIsNotNone(owner_b)
            assert owner_a is not None and owner_b is not None
            self.assertTrue(owner_a.is_self)
            self.assertFalse(owner_b.is_self)

            self.assertTrue(remove_claim(cfg_a, "SIM-2"))
            self.assertIsNone(resolve_owner(cfg_a, "SIM-2", now=1050.0))

    def test_external_rb_and_app_running_owners(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            other_wt = root / "other-wt"
            other_wt.mkdir()
            cfg = make_cfg(root, workspace=root / "my-wt")
            rb_dir = cfg.rb_claims_dir / "SIM-RB"
            rb_dir.mkdir(parents=True)
            (rb_dir / "owner").write_text(str(other_wt), encoding="utf-8")

            rb_owner = resolve_owner(cfg, "SIM-RB", now=1000.0)
            self.assertIsNotNone(rb_owner)
            assert rb_owner is not None
            self.assertEqual(rb_owner.source, "rb")
            self.assertFalse(rb_owner.is_self)

            app_owner = resolve_owner(cfg, "SIM-APP", app_running_fn=lambda _: True, now=1000.0)
            self.assertIsNotNone(app_owner)
            assert app_owner is not None
            self.assertEqual(app_owner.source, "app")

    def test_match_workspace_false_requires_explicit_self_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root, owner_label="mobpool-gui", workspace=root / "shared-ws")
            write_claim(cfg, "SIM-CLI", "ios", owner="cli-agent", ttl_sec=600, now=1000.0)
            write_claim(
                cfg,
                "SIM-GUI",
                "ios",
                owner="mobpool-gui",
                ttl_sec=600,
                now=1000.0,
                workspace="",
            )

            # Without match_workspace, same-workspace CLI claim is NOT self
            cli_owner = resolve_owner(
                cfg,
                "SIM-CLI",
                now=1050.0,
                match_workspace=False,
                self_owners={"mobpool-gui"},
            )
            self.assertIsNotNone(cli_owner)
            assert cli_owner is not None
            self.assertFalse(cli_owner.is_self)

            # Explicit self_owners match marks GUI claim as self
            gui_owner = resolve_owner(
                cfg,
                "SIM-GUI",
                now=1050.0,
                match_workspace=False,
                self_owners={"mobpool-gui"},
            )
            self.assertIsNotNone(gui_owner)
            assert gui_owner is not None
            self.assertTrue(gui_owner.is_self)


if __name__ == "__main__":
    unittest.main()
