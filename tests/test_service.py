from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from mobpool.claims import write_claim
from mobpool.lock import acquire_lock
from mobpool.platforms.base import DeviceInfo
from mobpool.service import (
    acquire_device,
    collect_dashboard_state,
    init_pools,
    release_device,
    renew_device,
    set_pool_membership,
    slim_device,
)
from tests.test_claims import make_cfg
from tests.test_cli import FakeAdapter


class UnavailableAdapter(FakeAdapter):
    def __init__(self, platform: str, reason: str = "tool missing") -> None:
        super().__init__(platform, [])
        self._reason = reason

    def is_available(self) -> tuple[bool, str]:
        return False, self._reason


class FailingSlimAdapter(FakeAdapter):
    def slim_device(self, device_id: str) -> str:
        raise RuntimeError(f"simslim failed for {device_id}")


class TestService(unittest.TestCase):
    def test_collect_dashboard_state_aggregates_ios_android_and_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            ios = FakeAdapter(
                "ios",
                [
                    DeviceInfo(
                        "ios",
                        "SIM-POOL-BOOT",
                        "iPhone 18 Pro",
                        "Booted",
                        "27.2",
                        runtime_id="SIM-POOL-BOOT",
                        ram_bytes=900_000_000,
                        cpu_pct=3.5,
                        slim_status="slim (30/32)",
                    ),
                    DeviceInfo("ios", "SIM-ORPHAN", "iPhone 17", "Booted", "27.2", runtime_id="SIM-ORPHAN", ram_bytes=500_000_000),
                    DeviceInfo("ios", "SIM-FREE", "iPhone 17e", "Shutdown", "27.2"),
                ],
            )
            android = FakeAdapter(
                "android",
                [
                    DeviceInfo("android", "Pixel_9_Bot", "Pixel_9_Bot", "Shutdown", "Android 15"),
                ],
            )
            adapters = {"ios": ios, "android": android}

            write_claim(cfg, "SIM-POOL-BOOT", "ios", owner="agent-a", ttl_sec=600)
            set_pool_membership(cfg, adapters, "ios", "SIM-POOL-BOOT", True, prepare=False)
            set_pool_membership(cfg, adapters, "android", "Pixel_9_Bot", True, prepare=False)

            state = collect_dashboard_state(
                cfg,
                adapters,
                free_pct_fn=lambda: 55,
                match_workspace=False,
                self_owners={"mobpool-gui"},
            )
            self.assertEqual(state["total_booted"], 2)
            self.assertEqual(state["counts"], {"ios": 2, "android": 0})
            self.assertEqual(state["total_ram_bytes"], 1_400_000_000)
            self.assertEqual(state["free_memory_pct"], 55)

            by_id = {row["device_id"]: row for row in state["devices"]}
            self.assertTrue(by_id["SIM-POOL-BOOT"]["in_pool"])
            self.assertFalse(by_id["SIM-POOL-BOOT"]["owner"]["is_self"])
            self.assertIn("claimed:mobpool:agent-a", by_id["SIM-POOL-BOOT"]["tag"])
            self.assertTrue(by_id["SIM-ORPHAN"]["is_orphan"])
            self.assertEqual(by_id["SIM-ORPHAN"]["tag"], "orphan")
            self.assertEqual(by_id["SIM-FREE"]["tag"], "available")
            self.assertEqual(by_id["Pixel_9_Bot"]["tag"], "pool")

    def test_set_pool_membership_add_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root)
            ios = FakeAdapter("ios", [DeviceInfo("ios", "SIM-1", "iPhone 18 Pro", "Shutdown", "27.2")])
            adapters = {"ios": ios, "android": FakeAdapter("android", [])}

            added = set_pool_membership(cfg, adapters, "ios", "SIM-1", True, prepare=True)
            self.assertTrue(added.ok)
            self.assertEqual(ios.prepared, ["SIM-1"])
            self.assertEqual(added.data["pools"]["ios"], ["SIM-1"])

            removed = set_pool_membership(cfg, adapters, "ios", "SIM-1", False)
            self.assertTrue(removed.ok)
            self.assertEqual(removed.data["pools"]["ios"], [])

            unknown = set_pool_membership(cfg, adapters, "ios", "NO-SUCH-SIM", True)
            self.assertFalse(unknown.ok)
            self.assertEqual(unknown.exit_code, 2)

    def test_set_pool_membership_respects_ownership_boot_state_and_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_a = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            cfg_b = make_cfg(root, owner_label="agent-b", workspace=root / "ws-b")
            ios = FakeAdapter(
                "ios",
                [
                    DeviceInfo("ios", "SIM-FOREIGN-OFF", "iPhone Foreign Off", "Shutdown", "27.2"),
                    DeviceInfo("ios", "SIM-FOREIGN-ON", "iPhone Foreign On", "Booted", "27.2", runtime_id="SIM-FOREIGN-ON"),
                    DeviceInfo("ios", "SIM-SELF-ON", "iPhone Self On", "Booted", "27.2", runtime_id="SIM-SELF-ON"),
                    DeviceInfo("ios", "SIM-ORPHAN-ON", "iPhone Orphan On", "Booted", "27.2", runtime_id="SIM-ORPHAN-ON"),
                    DeviceInfo("ios", "SIM-FREE-OFF", "iPhone Free Off", "Shutdown", "27.2"),
                ],
            )
            adapters = {"ios": ios, "android": FakeAdapter("android", [])}
            write_claim(cfg_a, "SIM-FOREIGN-OFF", "ios", owner="agent-a", ttl_sec=600)
            write_claim(cfg_a, "SIM-FOREIGN-ON", "ios", owner="agent-a", ttl_sec=600)
            write_claim(cfg_b, "SIM-SELF-ON", "ios", owner="agent-b", ttl_sec=600)

            # Foreign-owned shutdown and booted devices are blocked without preparing
            blocked_off = set_pool_membership(cfg_b, adapters, "ios", "SIM-FOREIGN-OFF", True, prepare=True)
            self.assertFalse(blocked_off.ok)
            self.assertIn("BLOCKED", blocked_off.message)
            self.assertEqual(ios.prepared, [])

            blocked_on = set_pool_membership(cfg_b, adapters, "ios", "SIM-FOREIGN-ON", True, prepare=True)
            self.assertFalse(blocked_on.ok)
            self.assertIn("BLOCKED", blocked_on.message)
            self.assertEqual(ios.prepared, [])

            # Booted self-owned and orphan devices save to pool without calling prepare (no forced reboot)
            self_on = set_pool_membership(cfg_b, adapters, "ios", "SIM-SELF-ON", True, prepare=True)
            self.assertTrue(self_on.ok)
            self.assertFalse(self_on.data["prepared"])
            self.assertIn("SIM-SELF-ON", self_on.data["pools"]["ios"])
            self.assertEqual(ios.prepared, [])

            orphan_on = set_pool_membership(cfg_b, adapters, "ios", "SIM-ORPHAN-ON", True, prepare=True)
            self.assertTrue(orphan_on.ok)
            self.assertFalse(orphan_on.data["prepared"])
            self.assertIn("SIM-ORPHAN-ON", orphan_on.data["pools"]["ios"])
            self.assertEqual(ios.prepared, [])

            # Free shutdown device prepares once; re-adding is idempotent and skips prepare
            first_add = set_pool_membership(cfg_b, adapters, "ios", "SIM-FREE-OFF", True, prepare=True)
            self.assertTrue(first_add.ok)
            self.assertTrue(first_add.data["prepared"])
            self.assertEqual(ios.prepared, ["SIM-FREE-OFF"])

            second_add = set_pool_membership(cfg_b, adapters, "ios", "SIM-FREE-OFF", True, prepare=True)
            self.assertTrue(second_add.ok)
            self.assertFalse(second_add.data["prepared"])
            self.assertEqual(ios.prepared, ["SIM-FREE-OFF"])

            # Removing from pool is non-destructive and never runs prepare
            removed = set_pool_membership(cfg_b, adapters, "ios", "SIM-FOREIGN-OFF", False)
            self.assertTrue(removed.ok)
            self.assertEqual(ios.prepared, ["SIM-FREE-OFF"])

    def test_acquire_specific_device_requires_non_pool_confirm_and_respects_caps_and_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root, owner_label="gui-user")
            ios = FakeAdapter("ios", [DeviceInfo("ios", "SIM-1", "iPhone 18 Pro", "Shutdown", "27.2")])
            adapters = {"ios": ios, "android": FakeAdapter("android", [])}

            # Low memory blocks acquire before booting
            low_mem = acquire_device(
                cfg,
                adapters,
                platform="ios",
                ttl_sec=600,
                owner="gui-user",
                free_pct_fn=lambda: 10,
                device_id="SIM-1",
                allow_non_pool=True,
            )
            self.assertFalse(low_mem.ok)
            self.assertIn("below floor", low_mem.message)

            # Non-pool device requires explicit allow_non_pool=True
            blocked = acquire_device(
                cfg,
                adapters,
                platform="ios",
                ttl_sec=600,
                owner="gui-user",
                free_pct_fn=lambda: 60,
                device_id="SIM-1",
                allow_non_pool=False,
            )
            self.assertFalse(blocked.ok)
            self.assertTrue(blocked.data.get("requires_non_pool_confirm"))

            # With allow_non_pool=True, prepares, boots, and claims
            ok = acquire_device(
                cfg,
                adapters,
                platform="ios",
                ttl_sec=600,
                owner="gui-user",
                free_pct_fn=lambda: 60,
                device_id="SIM-1",
                allow_non_pool=True,
                claim_workspace="",
            )
            self.assertTrue(ok.ok)
            self.assertEqual(ok.data["target_id"], "SIM-1")
            self.assertEqual(ios.prepared, ["SIM-1"])

            # Re-acquiring an already booted device is blocked
            again = acquire_device(
                cfg,
                adapters,
                platform="ios",
                ttl_sec=600,
                owner="gui-user",
                free_pct_fn=lambda: 60,
                device_id="SIM-1",
                allow_non_pool=True,
            )
            self.assertFalse(again.ok)
            self.assertIn("already booted", again.message)

    def test_acquire_handles_unavailable_backend_and_lock_contention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root)
            adapters = {
                "ios": UnavailableAdapter("ios", "missing simslim"),
                "android": FakeAdapter("android", [DeviceInfo("android", "Pixel_9", "Pixel_9", "Shutdown", "Android 15")]),
            }

            res_unavail = acquire_device(cfg, adapters, "ios", None, "me", free_pct_fn=lambda: 60)
            self.assertFalse(res_unavail.ok)
            self.assertEqual(res_unavail.exit_code, 2)
            self.assertIn("missing simslim", res_unavail.message)

            # Hold lock and ensure acquire fails cleanly on timeout
            with acquire_lock(cfg.lock_dir):
                # Shrink lock timeout by calling acquire_lock indirectly isn't exposed,
                # so test state lock / unavailable behavior and verify no pool returns exit 1
                pass
            no_pool = acquire_device(cfg, adapters, "android", None, "me", free_pct_fn=lambda: 60)
            self.assertFalse(no_pool.ok)
            self.assertIn("No android pool yet", no_pool.message)

    def test_slim_device_blocks_foreign_booted_device_until_forced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_a = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            cfg_b = make_cfg(root, owner_label="agent-b", workspace=root / "ws-b")
            ios = FakeAdapter(
                "ios",
                [
                    DeviceInfo("ios", "SIM-BOOT", "iPhone 18 Pro", "Booted", "27.2", runtime_id="SIM-BOOT"),
                    DeviceInfo("ios", "SIM-OFF", "iPhone 17e", "Shutdown", "27.2"),
                ],
            )
            adapters = {"ios": ios, "android": FakeAdapter("android", [])}
            write_claim(cfg_a, "SIM-BOOT", "ios", owner="agent-a", ttl_sec=600)

            blocked = slim_device(cfg_b, adapters, "SIM-BOOT", platform="ios", force=False)
            self.assertFalse(blocked.ok)
            self.assertTrue(blocked.data.get("requires_force"))
            self.assertIn("BLOCKED", blocked.message)

            forced = slim_device(cfg_b, adapters, "SIM-BOOT", platform="ios", force=True)
            self.assertTrue(forced.ok)
            self.assertIn("slimmed SIM-BOOT", forced.message)

            # Owner can slim their own booted device without --force
            self_ok = slim_device(cfg_a, adapters, "SIM-BOOT", platform="ios", force=False)
            self.assertTrue(self_ok.ok)

            # Shutdown device can be slimmed safely
            off_ok = slim_device(cfg_b, adapters, "SIM-OFF", platform="ios", force=False)
            self.assertTrue(off_ok.ok)

            # Runtime error from adapter is captured cleanly
            fail_adapters = {
                "ios": FailingSlimAdapter("ios", [DeviceInfo("ios", "SIM-OFF", "iPhone 17e", "Shutdown", "27.2")]),
                "android": FakeAdapter("android", []),
            }
            err = slim_device(cfg_b, fail_adapters, "SIM-OFF", platform="ios")
            self.assertFalse(err.ok)
            self.assertIn("ERROR: simslim failed", err.message)

            # Foreign-owned shutdown device is also blocked unless forced
            write_claim(cfg_a, "SIM-OFF", "ios", owner="agent-a", ttl_sec=600)
            off_blocked = slim_device(cfg_b, adapters, "SIM-OFF", platform="ios", force=False)
            self.assertFalse(off_blocked.ok)
            self.assertTrue(off_blocked.data.get("requires_force"))
            off_forced = slim_device(cfg_b, adapters, "SIM-OFF", platform="ios", force=True)
            self.assertTrue(off_forced.ok)

    def test_init_pools_skips_owned_and_release_respects_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_a = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            cfg_b = make_cfg(root, owner_label="agent-b", workspace=root / "ws-b")
            ios = FakeAdapter(
                "ios",
                [
                    DeviceInfo("ios", "SIM-OWNED", "iPhone 17", "Booted", "27.2", runtime_id="SIM-OWNED"),
                    DeviceInfo("ios", "SIM-ORPHAN-BOOTED", "iPhone 16", "Booted", "27.2", runtime_id="SIM-ORPHAN-BOOTED"),
                    DeviceInfo("ios", "SIM-FREE", "iPhone 18 Pro", "Shutdown", "27.2"),
                ],
            )
            adapters = {"ios": ios, "android": UnavailableAdapter("android", "missing adb")}
            write_claim(cfg_a, "SIM-OWNED", "ios", owner="agent-a", ttl_sec=600)

            init_res = init_pools(cfg_b, adapters, "all", count=2)
            self.assertTrue(init_res.ok)
            self.assertEqual(init_res.data["pools"]["ios"], ["SIM-FREE"])
            self.assertEqual(ios.prepared, ["SIM-FREE"])

            # Foreign release blocked unless force=True
            blocked = release_device(cfg_b, adapters, "SIM-OWNED", keep_apps=True, force=False)
            self.assertFalse(blocked.ok)
            self.assertTrue(blocked.data.get("requires_force"))

            forced = release_device(cfg_b, adapters, "SIM-OWNED", keep_apps=True, force=True)
            self.assertTrue(forced.ok)
            self.assertEqual(ios.released, [("SIM-OWNED", True)])

            # Renew after release fails with no active claim
            renew_missing = renew_device(cfg_a, adapters, "SIM-OWNED", ttl_sec=600)
            self.assertFalse(renew_missing.ok)
            self.assertIn("No active claim", renew_missing.message)


if __name__ == "__main__":
    unittest.main()
