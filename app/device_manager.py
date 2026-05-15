from __future__ import annotations

from app.devices.base import BaseDevice


class DeviceManager:
    def __init__(self, devices: dict[str, BaseDevice]) -> None:
        self.devices = devices

    def initialize_all(self) -> None:
        for device in self.devices.values():
            device.initialize()

    def shutdown_all(self) -> None:
        for device in self.devices.values():
            device.shutdown()

    def health_status(self) -> dict[str, dict]:
        return {
            key: {
                "name": device.name,
                "status": device.health.value,
                "healthy": device.healthy,
                "last_error": device.last_error,
            }
            for key, device in self.devices.items()
        }
