"""Platform adapters for iOS simulators and Android emulators."""

from mobpool.platforms.android import AndroidAdapter
from mobpool.platforms.base import DeviceInfo, PlatformAdapter
from mobpool.platforms.ios import IOSAdapter

__all__ = ["AndroidAdapter", "DeviceInfo", "IOSAdapter", "PlatformAdapter"]
