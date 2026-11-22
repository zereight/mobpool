"""iOS Simulator adapter wrapping xcrun simctl and simslim."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

from mobpool.config import MobpoolConfig
from mobpool.platforms.base import DeviceInfo


_IOS_RUNTIME_RE = re.compile(
    r"^com\.apple\.CoreSimulator\.SimRuntime\.iOS-(\d+)-(\d+)(.*)$"
)


def parse_ios_runtime_rank(runtime_key: str) -> tuple[int, int, int, str] | None:
    """Rank iOS runtimes: newest version first, plain iOS-X-Y ahead of suffixed."""
    match = _IOS_RUNTIME_RE.match(runtime_key)
    if not match:
        return None
    major, minor, suffix = int(match.group(1)), int(match.group(2)), match.group(3)
    return (major, minor, 1 if suffix == "" else 0, suffix)


def format_slim_status(disabled: int, total: int) -> str:
    if total <= 0:
        return "unknown (0/0)"
    label = "slim" if (disabled / total) > 0.5 else "NOT slim"
    return f"{label} ({disabled}/{total})"


def select_ios_pool_candidates(
    devices_by_runtime: dict[str, list[dict[str, object]]],
    count: int,
    owned_ids: set[str],
) -> list[str]:
    ranked = sorted(
        (
            (rank, runtime_key, devs)
            for runtime_key, devs in devices_by_runtime.items()
            if (rank := parse_ios_runtime_rank(runtime_key)) is not None
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    picks: list[str] = []
    for _rank, _runtime_key, devs in ranked:
        iphones = [
            dev
            for dev in devs
            if "iPhone" in str(dev.get("name", ""))
            and dev.get("isAvailable", True)
            and str(dev.get("udid", "")) not in owned_ids
        ]
        if not iphones:
            continue
        for dev in iphones:
            udid = str(dev["udid"])
            if udid not in picks:
                picks.append(udid)
            if len(picks) >= count:
                return picks
    return picks


class IOSAdapter:
    platform = "ios"

    def __init__(self, cfg: MobpoolConfig) -> None:
        self.cfg = cfg

    def is_available(self) -> tuple[bool, str]:
        if not shutil.which("xcrun"):
            return False, "missing xcrun (install Xcode)"
        if not shutil.which("simslim"):
            return False, "missing simslim (brew install mobai-app/tap/simslim)"
        return True, "ok"

    def _simctl_json(self, *args: str) -> dict[str, object]:
        try:
            proc = subprocess.run(
                ["xcrun", "simctl", "list", "devices", *args, "--json"],
                capture_output=True,
                text=True,
                timeout=25,
            )
            return json.loads(proc.stdout or "{}")
        except Exception:
            return {}

    def _simslim_snapshot(self) -> dict[str, dict[str, object]]:
        if not shutil.which("simslim"):
            return {}
        try:
            proc = subprocess.run(
                ["simslim", "top", "--json"],
                capture_output=True,
                text=True,
                timeout=25,
            )
            data = json.loads(proc.stdout or "{}")
            return {
                str(item["udid"]): item
                for item in data.get("sims", [])
                if item.get("udid")
            }
        except Exception:
            return {}

    def list_available(self) -> list[DeviceInfo]:
        devs_map = self._simctl_json("available").get("devices", {})
        if not isinstance(devs_map, dict):
            return []
        result: list[DeviceInfo] = []
        for runtime_key, devs in devs_map.items():
            if "iOS" not in runtime_key or not isinstance(devs, list):
                continue
            os_ver = runtime_key.rsplit("iOS-", 1)[-1].replace("-", ".")
            for dev in devs:
                udid = str(dev.get("udid", ""))
                if not udid:
                    continue
                result.append(
                    DeviceInfo(
                        platform="ios",
                        device_id=udid,
                        name=str(dev.get("name", udid)),
                        state=str(dev.get("state", "Shutdown")),
                        os_version=os_ver,
                        runtime_id=udid,
                    )
                )
        return result

    def list_booted(self) -> list[DeviceInfo]:
        snap = self._simslim_snapshot()
        booted: list[DeviceInfo] = []
        for dev in self.list_available():
            if dev.state != "Booted":
                continue
            metric = snap.get(dev.device_id, {})
            mem = metric.get("memory") or {}
            disabled = int(metric.get("managedDisabled", 0) or 0)
            total = int(metric.get("managedTotal", 0) or 0)
            booted.append(
                DeviceInfo(
                    platform="ios",
                    device_id=dev.device_id,
                    name=str(metric.get("name") or dev.name),
                    state="Booted",
                    os_version=str(metric.get("osVersion") or dev.os_version),
                    runtime_id=dev.device_id,
                    ram_bytes=int(mem.get("bytes", 0) or 0),
                    processes=int(mem.get("processes", 0) or 0),
                    cpu_pct=float(mem.get("cpu", 0.0) or 0.0),
                    slim_status=format_slim_status(disabled, total),
                )
            )
        return booted

    def select_pool(self, count: int, owned_ids: set[str]) -> list[str]:
        devs_map = self._simctl_json("available").get("devices", {})
        if not isinstance(devs_map, dict):
            return []
        return select_ios_pool_candidates(devs_map, count=count, owned_ids=owned_ids)

    def prepare_pool_device(self, device_id: str) -> None:
        subprocess.run(
            [
                "simslim",
                "on",
                device_id,
                "--except",
                self.cfg.simslim_except,
                "--preserve-boot-state",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )

    def slim_device(self, device_id: str) -> str:
        proc = subprocess.run(
            ["simslim", "on", device_id, "--except", self.cfg.simslim_except],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"simslim on failed for {device_id}")
        return proc.stdout.strip() or f"slimmed {device_id}"

    def boot_and_slim(self, device_id: str) -> str:
        boot = subprocess.run(
            ["simslim", "boot", device_id],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if boot.returncode != 0:
            raise RuntimeError(boot.stderr.strip() or f"simslim boot failed for {device_id}")
        verify = subprocess.run(
            ["simslim", "verify", device_id, "--except", self.cfg.simslim_except],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if verify.returncode != 0:
            self.slim_device(device_id)
        return device_id

    def release_device(self, device_id: str, keep_apps: bool = False) -> bool:
        if not keep_apps:
            self._uninstall_user_apps(device_id)
            subprocess.run(
                ["xcrun", "simctl", "keychain", device_id, "reset"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
        proc = subprocess.run(
            ["simslim", "shutdown", device_id],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode == 0

    def _uninstall_user_apps(self, device_id: str) -> None:
        try:
            listed = subprocess.run(
                ["xcrun", "simctl", "listapps", device_id],
                capture_output=True,
                timeout=20,
            )
            if listed.returncode != 0 or not listed.stdout:
                return
            converted = subprocess.run(
                ["plutil", "-convert", "json", "-o", "-", "-"],
                input=listed.stdout,
                capture_output=True,
                timeout=15,
            )
            apps = json.loads(converted.stdout.decode("utf-8", errors="ignore") or "{}")
        except Exception:
            return
        for bundle_id, meta in apps.items():
            if isinstance(meta, dict) and meta.get("ApplicationType") == "User":
                subprocess.run(
                    ["xcrun", "simctl", "uninstall", device_id, bundle_id],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                )

    def is_app_running(self, device_id: str) -> bool:
        if not self.cfg.app_id:
            return False
        try:
            proc = subprocess.run(
                ["xcrun", "simctl", "spawn", device_id, "launchctl", "list"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return f"UIKitApplication:{self.cfg.app_id}" in proc.stdout
        except Exception:
            return False

    def shutdown_hint(self, device: DeviceInfo) -> str:
        return f"simslim shutdown {device.device_id}"
