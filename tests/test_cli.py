from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from mobpool.cli import run_cli
from mobpool.platforms.base import DeviceInfo
from tests.test_claims import make_cfg


class FakeAdapter:
    def __init__(self, platform: str, devices: list[DeviceInfo]) -> None:
        self.platform = platform
        self.devices: dict[str, DeviceInfo] = {d.device_id: d for d in devices}
        self.prepared: list[str] = []
        self.released: list[tuple[str, bool]] = []

    def is_available(self) -> tuple[bool, str]:
        return True, "ok"

    def list_available(self) -> list[DeviceInfo]:
        return list(self.devices.values())

    def list_booted(self) -> list[DeviceInfo]:
        return [d for d in self.devices.values() if d.state == "Booted"]

    def select_pool(self, count: int, owned_ids: set[str]) -> list[str]:
        return [d.device_id for d in self.devices.values() if d.device_id not in owned_ids][:count]

    def prepare_pool_device(self, device_id: str) -> None:
        self.prepared.append(device_id)

    def boot_and_slim(self, device_id: str) -> str:
        dev = self.devices[device_id]
        runtime_id = "emulator-5554" if self.platform == "android" else device_id
        self.devices[device_id] = DeviceInfo(
            platform=self.platform,
            device_id=dev.device_id,
            name=dev.name,
            state="Booted",
            os_version=dev.os_version,
            runtime_id=runtime_id,
            ram_bytes=800_000_000,
            cpu_pct=2.0,
            slim_status="slim (30/32)" if self.platform == "ios" else "flags-slim",
        )
        return runtime_id

    def slim_device(self, device_id: str) -> str:
        return f"slimmed {device_id}"

    def release_device(self, device_id: str, keep_apps: bool = False) -> bool:
        self.released.append((device_id, keep_apps))
        dev = self.devices[device_id]
        self.devices[device_id] = DeviceInfo(
            platform=self.platform,
            device_id=dev.device_id,
            name=dev.name,
            state="Shutdown",
            os_version=dev.os_version,
            runtime_id="",
        )
        return True

    def is_app_running(self, device_id: str) -> bool:
        return False

    def shutdown_hint(self, device: DeviceInfo) -> str:
        return f"shutdown {device.target_id}"


class TestCLI(unittest.TestCase):
    def test_init_acquire_renew_and_release_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_a = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            cfg_b = make_cfg(root, owner_label="agent-b", workspace=root / "ws-b")
            adapters = {
                "ios": FakeAdapter("ios", [DeviceInfo("ios", "SIM-1", "iPhone 18 Pro", "Shutdown", "27.2")]),
                "android": FakeAdapter("android", [DeviceInfo("android", "Pixel_9_Bot", "Pixel_9_Bot", "Shutdown", "Android 15")]),
            }

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(["init", "--platform", "all"], cfg=cfg_a, adapters=adapters, free_pct_fn=lambda: 60)
            self.assertEqual(rc, 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(
                    ["acquire", "--platform", "android", "--ttl", "1800"],
                    cfg=cfg_a,
                    adapters=adapters,
                    free_pct_fn=lambda: 60,
                )
            self.assertEqual(rc, 0)
            self.assertIn("ACQUIRED emulator-5554", buf.getvalue())

            # Foreign agent cannot release agent-a's emulator (even when passing serial)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(["release", "emulator-5554"], cfg=cfg_b, adapters=adapters, free_pct_fn=lambda: 60)
            self.assertEqual(rc, 1)
            self.assertIn("BLOCKED", buf.getvalue())

            # Renew works using ADB serial
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(["renew", "emulator-5554", "--ttl", "3600"], cfg=cfg_a, adapters=adapters, free_pct_fn=lambda: 60)
            self.assertEqual(rc, 0)
            self.assertIn("RENEWED Pixel_9_Bot", buf.getvalue())

            # Audit JSON reports the claimed Android emulator
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(["audit", "--json"], cfg=cfg_a, adapters=adapters, free_pct_fn=lambda: 60)
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["total_booted"], 1)
            self.assertEqual(data["devices"][0]["target_id"], "emulator-5554")
            self.assertIn("claimed:mobpool:agent-a", data["devices"][0]["tag"])

            # Owner can release cleanly
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(["release", "emulator-5554"], cfg=cfg_a, adapters=adapters, free_pct_fn=lambda: 60)
            self.assertEqual(rc, 0)
            self.assertIn("RELEASED Pixel_9_Bot", buf.getvalue())

    def test_cli_slim_respects_ownership_and_gui_rejects_non_loopback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_a = make_cfg(root, owner_label="agent-a", workspace=root / "ws-a")
            cfg_b = make_cfg(root, owner_label="agent-b", workspace=root / "ws-b")
            adapters = {
                "ios": FakeAdapter("ios", [DeviceInfo("ios", "SIM-1", "iPhone 18 Pro", "Shutdown", "27.2")]),
                "android": FakeAdapter("android", []),
            }

            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    run_cli(["init", "--platform", "ios"], cfg=cfg_a, adapters=adapters, free_pct_fn=lambda: 60),
                    0,
                )
                self.assertEqual(
                    run_cli(["acquire", "--platform", "ios"], cfg=cfg_a, adapters=adapters, free_pct_fn=lambda: 60),
                    0,
                )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(["slim", "SIM-1", "--platform", "ios"], cfg=cfg_b, adapters=adapters, free_pct_fn=lambda: 60)
            self.assertEqual(rc, 1)
            self.assertIn("BLOCKED", buf.getvalue())

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(
                    ["slim", "SIM-1", "--platform", "ios", "--force"],
                    cfg=cfg_b,
                    adapters=adapters,
                    free_pct_fn=lambda: 60,
                )
            self.assertEqual(rc, 0)
            self.assertIn("slimmed SIM-1", buf.getvalue())

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_cli(
                    ["gui", "--host", "0.0.0.0", "--no-open"],
                    cfg=cfg_a,
                    adapters=adapters,
                    free_pct_fn=lambda: 60,
                )
            self.assertEqual(rc, 2)
            self.assertIn("non-loopback", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
