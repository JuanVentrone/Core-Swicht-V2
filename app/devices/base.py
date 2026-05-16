from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class DeviceHealth(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"


class BaseDevice(ABC):
    def __init__(self, device_id: str, name: str) -> None:
        self.device_id = device_id
        self.name = name
        self._healthy = False
        self._last_error = ""

    @property
    def healthy(self) -> bool:
        return self._healthy

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def health(self) -> DeviceHealth:
        return DeviceHealth.ONLINE if self.healthy else DeviceHealth.OFFLINE

    @abstractmethod
    def initialize(self) -> None:
        """Initialize resources needed by the device."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release resources before app shutdown."""

