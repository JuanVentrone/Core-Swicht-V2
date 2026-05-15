from __future__ import annotations

from app.devices.base import BaseDevice
from app.models import Contactor
from app.services import FarmController


class RelayControllerDevice(BaseDevice):
    def __init__(self, contactors: dict[str, Contactor], webhook_url: str, webhook_token: str) -> None:
        super().__init__(device_id="relay-controller", name="Relay Controller")
        self.controller = FarmController(
            contactors=contactors,
            webhook_url=webhook_url,
            webhook_token=webhook_token,
        )

    def initialize(self) -> None:
        self._healthy = len(self.controller.contactors) > 0
        self._last_error = "" if self._healthy else "No relay contactors configured"

    def shutdown(self) -> None:
        self._healthy = False
