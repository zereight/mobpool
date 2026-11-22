"""Common device model and platform adapter interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DeviceInfo:
    platform: str
    device_id: str
    name: str
    state: str
    os_version: str = ""
    runtime_id: str = ""
    ram_bytes: int = 0
    processes: int = 0
    cpu_pct: float = 0.0
    slim_status: str = ""

    @property
    def target_id(self) -> str:
        """Identifier passed to Argent / adb / simctl when booted."""
        return self.runtime_id or self.device_id


class PlatformAdapter(Protocol):
    platform: str

    def is_available(self) -> tuple[bool, str]: ...

    def list_available(self) -> list[DeviceInfo]: ...

    def list_booted(self) -> list[DeviceInfo]: ...

    def select_pool(self, count: int, owned_ids: set[str]) -> list[str]: ...

    def prepare_pool_device(self, device_id: str) -> None: ...

    def boot_and_slim(self, device_id: str) -> str: ...

    def slim_device(self, device_id: str) -> str: ...

    def release_device(self, device_id: str, keep_apps: bool = False) -> bool: ...

    def is_app_running(self, device_id: str) -> bool: ...

    def shutdown_hint(self, device: DeviceInfo) -> str: ...
