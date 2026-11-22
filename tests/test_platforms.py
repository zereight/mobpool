from __future__ import annotations

import unittest

from mobpool.platforms.android import (
    parse_adb_emulators,
    parse_avd_name_output,
    parse_qemu_metrics,
    select_android_pool_candidates,
)
from mobpool.platforms.ios import (
    format_slim_status,
    parse_ios_runtime_rank,
    select_ios_pool_candidates,
)


class TestPlatformHelpers(unittest.TestCase):
    def test_ios_runtime_prefers_plain_over_suffixed(self) -> None:
        plain = parse_ios_runtime_rank("com.apple.CoreSimulator.SimRuntime.iOS-27-2")
        suffixed = parse_ios_runtime_rank(
            "com.apple.CoreSimulator.SimRuntime.iOS-27-2-iPhone19-4"
        )
        self.assertIsNotNone(plain)
        self.assertIsNotNone(suffixed)
        assert plain is not None and suffixed is not None
        self.assertGreater(plain, suffixed)

    def test_ios_pool_skips_owned_and_picks_plain_runtime(self) -> None:
        devices = {
            "com.apple.CoreSimulator.SimRuntime.iOS-27-2-iPhone19-4": [
                {"udid": "U-DUO", "name": "iPhone Duo", "isAvailable": True}
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-27-2": [
                {"udid": "U-OWNED", "name": "iPhone 17", "isAvailable": True},
                {"udid": "U-FREE1", "name": "iPhone 18 Pro", "isAvailable": True},
                {"udid": "U-FREE2", "name": "iPhone 18 Pro Max", "isAvailable": True},
            ],
        }
        picks = select_ios_pool_candidates(devices, count=2, owned_ids={"U-OWNED"})
        self.assertEqual(picks, ["U-FREE1", "U-FREE2"])

    def test_ios_slim_status_ratio(self) -> None:
        self.assertEqual(format_slim_status(30, 32), "slim (30/32)")
        self.assertEqual(format_slim_status(5, 32), "NOT slim (5/32)")

    def test_android_parsing_and_selection(self) -> None:
        adb_out = "List of devices attached\nemulator-5554\tdevice\nemulator-5556\toffline\n"
        self.assertEqual(
            parse_adb_emulators(adb_out),
            [("emulator-5554", "device"), ("emulator-5556", "offline")],
        )
        self.assertEqual(parse_avd_name_output("Pixel_9_Bot\r\nOK\r\n"), "Pixel_9_Bot")
        picks = select_android_pool_candidates(
            ["Pixel_9_Pro_Fold_2", "Pixel_9_Bot", "Medium_Phone"],
            count=2,
            owned_ids={"Medium_Phone"},
        )
        self.assertEqual(picks, ["Pixel_9_Bot", "Pixel_9_Pro_Fold_2"])

        ps_out = "  2048000  12.5 /path/qemu-system-aarch64 -avd Pixel_9_Bot -no-audio\n"
        rss, cpu = parse_qemu_metrics(ps_out, "Pixel_9_Bot")
        self.assertEqual(rss, 2048000 * 1024)
        self.assertAlmostEqual(cpu, 12.5)


if __name__ == "__main__":
    unittest.main()
