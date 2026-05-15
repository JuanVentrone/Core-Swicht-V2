from __future__ import annotations

from app.models import Contactor
from app.services import FarmController


class AlarmController:
    def __init__(self, devices: dict[str, Contactor], switcher: FarmController) -> None:
        self.devices = devices
        self.switcher = switcher

    def switch_buzzer(self, estado: bool) -> dict:
        buzzer = self.devices.get("BOCINA")
        if buzzer is None:
            return {"success": False, "error": "Bocina is not configured"}
        return self.switcher.ctr_contactor(buzzer, estado)

    def switch_lights(self, estado: bool) -> dict:
        results: dict[str, dict] = {}
        for key in ("LIGHT1", "LIGHT2", "LIGHT3"):
            light = self.devices.get(key)
            if light is None:
                results[key] = {"success": False, "error": f"{key} is not configured"}
                continue
            results[key] = self.switcher.ctr_contactor(light, estado)

        return {
            "success": all(item.get("success", False) for item in results.values()),
            "requested_state": estado,
            "results": results,
        }
