from __future__ import annotations

from collections.abc import Callable

from app.devices.base import BaseDevice


class DeviceManager:
    def __init__(
        self,
        devices: dict[str, BaseDevice],
        startup_gate: Callable[[], None] | None = None,
    ) -> None:
        self.devices = devices
        self.startup_gate = startup_gate

    def initialize_all(self) -> None:
        multimeter = self.devices.get("industrial_multimeter")
        if multimeter is not None:
            multimeter.initialize()
            if self.startup_gate is not None:
                self.startup_gate()
            for key, device in self.devices.items():
                if device is multimeter:
                    continue
                device.initialize()
        else:
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
