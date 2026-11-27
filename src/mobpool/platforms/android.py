"""Android Emulator adapter wrapping adb, emulator, and optional avdslim."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from mobpool.config import MobpoolConfig
from mobpool.platforms.base import DeviceInfo


_ADB_DEVICE_RE = re.compile(r"^(emulator-\d+)\s+(\S+)")


def find_android_tool(name: str, subdirs: tuple[str, ...]) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct
    sdk_roots = [
        os.environ.get("ANDROID_HOME", ""),
        os.environ.get("ANDROID_SDK_ROOT", ""),
        str(Path.home() / "Library" / "Android" / "sdk"),
    ]
    for root in sdk_roots:
        if not root:
            continue
        for sub in subdirs:
            candidate = Path(root) / sub / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def parse_adb_emulators(output: str) -> list[tuple[str, str]]:
    """Return [(serial, adb_state)] for running Android emulators."""
    results: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = _ADB_DEVICE_RE.match(line.strip())
        if match:
            results.append((match.group(1), match.group(2)))
    return results


def parse_avd_name_output(output: str) -> str:
    """Extract AVD name from `adb -s <serial> emu avd name` output."""
    for line in output.splitlines():
        cleaned = line.strip()
        if cleaned and cleaned.upper() != "OK":
            return cleaned
    return ""


def select_android_pool_candidates(
    avds: list[str],
    count: int,
    owned_ids: set[str],
) -> list[str]:
    """Prefer non-foldable AVDs first, then fall back to remaining AVDs."""
    free = [avd for avd in avds if avd not in owned_ids]
    standard = [avd for avd in free if "fold" not in avd.lower()]
    foldables = [avd for avd in free if "fold" in avd.lower()]
    return (standard + foldables)[:count]


def parse_qemu_metrics(ps_output: str, avd_name: str) -> tuple[int, float]:
    """Return (rss_bytes, cpu_pct) for the qemu process running `avd_name`."""
    target_flag = f"-avd {avd_name}"
    total_rss_kb = 0
    total_cpu = 0.0
    for line in ps_output.splitlines():
        if target_flag not in line:
            continue
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            rss_kb = int(parts[0])
            cpu = float(parts[1])
        except ValueError:
            continue
        total_rss_kb += rss_kb
        total_cpu += cpu
    return total_rss_kb * 1024, total_cpu


class AndroidAdapter:
    platform = "android"

    def __init__(self, cfg: MobpoolConfig) -> None:
        self.cfg = cfg
        self.adb = find_android_tool("adb", ("platform-tools",))
        self.emulator = find_android_tool("emulator", ("emulator",))
        self.avdslim = shutil.which("avdslim")

    def is_available(self) -> tuple[bool, str]:
        if not self.adb:
            return False, "missing adb (install Android SDK platform-tools)"
        if not self.emulator:
            return False, "missing emulator (install Android SDK emulator)"
        return True, "ok"

    def slim_capability(self) -> tuple[bool, str]:
        if self.avdslim:
            return True, "avdslim"
        return False, "avdslim not installed (lightweight emulator boot flags apply on boot)"

    def _list_avd_names(self) -> list[str]:
        if not self.emulator:
            return []
        try:
            proc = subprocess.run(
                [self.emulator, "-list-avds"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        except Exception:
            return []

    def _booted_serial_map(self) -> dict[str, str]:
        """Map avd_name -> adb serial for currently running emulators."""
        if not self.adb:
            return {}
        try:
            proc = subprocess.run(
                [self.adb, "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            return {}
        mapping: dict[str, str] = {}
        for serial, state in parse_adb_emulators(proc.stdout):
            if state not in ("device", "offline"):
                continue
            avd = self._avd_for_serial(serial) or serial
            mapping[avd] = serial
        return mapping

    def _avd_for_serial(self, serial: str) -> str:
        if not self.adb:
            return ""
        try:
            proc = subprocess.run(
                [self.adb, "-s", serial, "emu", "avd", "name"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return parse_avd_name_output(proc.stdout)
        except Exception:
            return ""

    def _android_version(self, serial: str) -> str:
        if not self.adb:
            return ""
        try:
            proc = subprocess.run(
                [self.adb, "-s", serial, "shell", "getprop", "ro.build.version.release"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            ver = proc.stdout.strip()
            return f"Android {ver}" if ver else ""
        except Exception:
            return ""

    def _ps_snapshot(self) -> str:
        try:
            proc = subprocess.run(
                ["ps", "-axo", "rss=,pcpu=,command="],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.stdout
        except Exception:
            return ""

    def list_available(self) -> list[DeviceInfo]:
        booted = self._booted_serial_map()
        avds = self._list_avd_names()
        all_names = list(dict.fromkeys([*avds, *booted.keys()]))
        return [
            DeviceInfo(
                platform="android",
                device_id=avd,
                name=avd,
                state="Booted" if avd in booted else "Shutdown",
                runtime_id=booted.get(avd, ""),
            )
            for avd in all_names
        ]

    def list_all_with_metrics(self) -> list[DeviceInfo]:
        booted = self._booted_serial_map()
        avds = self._list_avd_names()
        all_names = list(dict.fromkeys([*avds, *booted.keys()]))
        ps_out = self._ps_snapshot() if booted else ""
        slim_tag = "avdslim" if self.avdslim else "flags-slim"
        devices: list[DeviceInfo] = []
        for avd in all_names:
            serial = booted.get(avd, "")
            if serial:
                ram_bytes, cpu_pct = parse_qemu_metrics(ps_out, avd)
                devices.append(
                    DeviceInfo(
                        platform="android",
                        device_id=avd,
                        name=avd,
                        state="Booted",
                        os_version=self._android_version(serial),
                        runtime_id=serial,
                        ram_bytes=ram_bytes,
                        processes=1 if ram_bytes else 0,
                        cpu_pct=cpu_pct,
                        slim_status=slim_tag,
                    )
                )
            else:
                devices.append(
                    DeviceInfo(
                        platform="android",
                        device_id=avd,
                        name=avd,
                        state="Shutdown",
                        runtime_id="",
                    )
                )
        return devices

    def list_booted(self) -> list[DeviceInfo]:
        booted = self._booted_serial_map()
        if not booted:
            return []
        ps_out = self._ps_snapshot()
        slim_tag = "avdslim" if self.avdslim else "flags-slim"
        devices: list[DeviceInfo] = []
        for avd, serial in booted.items():
            ram_bytes, cpu_pct = parse_qemu_metrics(ps_out, avd)
            devices.append(
                DeviceInfo(
                    platform="android",
                    device_id=avd,
                    name=avd,
                    state="Booted",
                    os_version=self._android_version(serial),
                    runtime_id=serial,
                    ram_bytes=ram_bytes,
                    processes=1 if ram_bytes else 0,
                    cpu_pct=cpu_pct,
                    slim_status=slim_tag,
                )
            )
        return devices

    def select_pool(self, count: int, owned_ids: set[str]) -> list[str]:
        return select_android_pool_candidates(
            self._list_avd_names(), count=count, owned_ids=owned_ids
        )

    def prepare_pool_device(self, device_id: str) -> None:
        if self.avdslim:
            subprocess.run(
                [self.avdslim, "on", device_id],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )

    def slim_device(self, device_id: str) -> str:
        if not self.avdslim:
            return (
                f"avdslim not installed; {device_id} uses lightweight boot flags: "
                + " ".join(self.cfg.android_flags)
            )
        proc = subprocess.run(
            [self.avdslim, "on", device_id],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"avdslim on failed for {device_id}")
        return proc.stdout.strip() or f"slimmed {device_id}"

    def boot_and_slim(self, device_id: str, timeout_sec: float = 120.0) -> str:
        if not self.emulator or not self.adb:
            raise RuntimeError("Android SDK emulator/adb not found")
        existing = self._booted_serial_map().get(device_id)
        if existing:
            return existing

        cmd = [self.emulator, "-avd", device_id, *self.cfg.android_flags]
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        deadline = time.monotonic() + timeout_sec
        serial = ""
        while time.monotonic() < deadline:
            serial = self._booted_serial_map().get(device_id, "")
            if serial:
                boot_check = subprocess.run(
                    [self.adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if boot_check.stdout.strip() == "1":
                    return serial
            time.sleep(2.0)
        raise RuntimeError(
            f"Timed out waiting for Android AVD {device_id} to finish booting."
        )

    def _resolve_serial(self, device_or_serial: str) -> str:
        if device_or_serial.startswith("emulator-"):
            return device_or_serial
        return self._booted_serial_map().get(device_or_serial, "")

    def release_device(self, device_id: str, keep_apps: bool = False) -> bool:
        if not self.adb:
            return False
        serial = self._resolve_serial(device_id)
        if not serial:
            return True
        if not keep_apps:
            self._uninstall_third_party_apps(serial)
        proc = subprocess.run(
            [self.adb, "-s", serial, "emu", "kill"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode == 0

    def _uninstall_third_party_apps(self, serial: str) -> None:
        if not self.adb:
            return
        try:
            proc = subprocess.run(
                [self.adb, "-s", serial, "shell", "pm", "list", "packages", "-3"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception:
            return
        for line in proc.stdout.splitlines():
            pkg = line.strip().removeprefix("package:")
            if pkg:
                subprocess.run(
                    [self.adb, "-s", serial, "uninstall", pkg],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                )

    def is_app_running(self, device_id: str) -> bool:
        if not self.adb or not self.cfg.app_id:
            return False
        serial = self._resolve_serial(device_id)
        if not serial:
            return False
        try:
            proc = subprocess.run(
                [self.adb, "-s", serial, "shell", "pidof", self.cfg.app_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.returncode == 0 and bool(proc.stdout.strip())
        except Exception:
            return False

    def shutdown_hint(self, device: DeviceInfo) -> str:
        target = device.runtime_id or device.device_id
        return f"adb -s {target} emu kill"
