from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from urllib import error, request

import tinytuya

from app.models import Contactor

logger = logging.getLogger("farm-control")


class FarmController:
    def __init__(
        self,
        contactors: dict[str, Contactor],
        webhook_url: str = "",
        webhook_token: str = "",
    ) -> None:
        self.contactors = contactors
        self.webhook_url = webhook_url.strip()
        self.webhook_token = webhook_token.strip()
        self._thread_lock = threading.Lock()
        self._switch_thread: threading.Thread | None = None

    def _get_contactor_key(self, contactor_obj: Contactor) -> str:
        for key, value in self.contactors.items():
            if value is contactor_obj:
                return key
        return contactor_obj.name

    def _emit_webhook_event(self, contactor_key: str, result: dict) -> None:
        if not self.webhook_url:
            return

        payload = {
            "event": "switch_changed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_key": contactor_key,
            "name": result.get("name", contactor_key),
            "requested_state": "ON" if result.get("requested_state") else "OFF",
            "success": bool(result.get("success")),
            "device_response": result.get("device_response"),
            "error": result.get("error"),
            "source": "farm-control-api",
        }

        def _send() -> None:
            body = json.dumps(payload).encode("utf-8")
            req = request.Request(
                self.webhook_url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            if self.webhook_token:
                req.add_header("X-Webhook-Token", self.webhook_token)

            try:
                with request.urlopen(req, timeout=3) as response:
                    logger.info(
                        "Webhook sent for %s with status %s",
                        contactor_key,
                        response.status,
                    )
            except error.URLError as exc:
                logger.warning("Webhook delivery failed for %s: %s", contactor_key, exc)
            except Exception as exc:  # broad by design for network errors
                logger.warning("Unexpected webhook error for %s: %s", contactor_key, exc)

        threading.Thread(
            target=_send,
            daemon=True,
            name=f"webhook-{contactor_key.lower()}",
        ).start()

    def ctr_contactor(self, contactor_obj: Contactor, estado: bool) -> dict:
        device = None
        result: dict | None = None
        contactor_key = self._get_contactor_key(contactor_obj)
        try:
            if contactor_obj.version != "3.4":
                logger.warning(
                    "Contactor %s version '%s' overridden to 3.4",
                    contactor_obj.name,
                    contactor_obj.version,
                )

            device = tinytuya.OutletDevice(
                dev_id=contactor_obj.id,
                address=contactor_obj.ip,
                local_key=contactor_obj.key,
                version=3.4,
            )
            device.set_version(3.4)
            device.set_socketPersistent(True)

            logger.info(
                "Handshake status request for %s (%s)",
                contactor_obj.name,
                contactor_obj.ip,
            )
            handshake = device.status()
            logger.debug("Handshake response for %s: %s", contactor_obj.name, handshake)

            logger.info("Setting %s to %s", contactor_obj.name, "ON" if estado else "OFF")
            response = device.set_status(estado, 1)
            result = {
                "success": bool(response),
                "name": contactor_obj.name,
                "requested_state": estado,
                "device_response": response,
            }
            return result
        except Exception as exc:  # broad by design for network/device errors
            logger.exception("Error switching contactor %s: %s", contactor_obj.name, exc)
            result = {
                "success": False,
                "name": contactor_obj.name,
                "requested_state": estado,
                "error": str(exc),
            }
            return result
        finally:
            try:
                if result is not None:
                    self._emit_webhook_event(contactor_key, result)
            except Exception as webhook_exc:
                logger.warning(
                    "Webhook dispatch setup failed for %s: %s",
                    contactor_obj.name,
                    webhook_exc,
                )
            if device is not None:
                try:
                    device.close()
                except Exception as close_exc:
                    logger.warning(
                        "Error closing socket for %s: %s",
                        contactor_obj.name,
                        close_exc,
                    )

    def _run_sequential_on(self) -> None:
        ordered_keys = ("C1", "C2", "C3")
        for idx, key in enumerate(ordered_keys):
            contactor = self.contactors.get(key)
            if contactor is None:
                logger.warning("Contactor %s not found in config", key)
                continue

            self.ctr_contactor(contactor, True)
            if idx < len(ordered_keys) - 1:
                logger.info("Waiting 180 seconds before next contactor")
                time.sleep(180)
        logger.info("Sequential ON routine finished")

    def General_Switch_System(self, estado: bool) -> dict:
        if estado:
            with self._thread_lock:
                if self._switch_thread and self._switch_thread.is_alive():
                    return {
                        "accepted": False,
                        "message": "Sequential ON routine is already running",
                    }

                self._switch_thread = threading.Thread(
                    target=self._run_sequential_on,
                    daemon=True,
                    name="sequential-on-thread",
                )
                self._switch_thread.start()
            return {
                "accepted": True,
                "message": "Sequential ON routine started in background",
            }

        results = {}
        for key in ("C1", "C2", "C3"):
            contactor = self.contactors.get(key)
            if contactor is None:
                results[key] = {"success": False, "error": "Not configured"}
                continue
            results[key] = self.ctr_contactor(contactor, False)
        return {"accepted": True, "message": "Immediate OFF executed", "results": results}

    def General_Status(self) -> dict:
        status_map = {}
        for key, contactor in self.contactors.items():
            device = None
            try:
                device = tinytuya.OutletDevice(
                    dev_id=contactor.id,
                    address=contactor.ip,
                    local_key=contactor.key,
                    version=3.4,
                )
                device.set_version(3.4)
                device.set_socketPersistent(True)
                data = device.status()
                dps = data.get("dps", {}) if isinstance(data, dict) else {}
                raw_state = dps.get("1")
                status_map[key] = {
                    "name": contactor.name,
                    "state": "ON" if raw_state else "OFF",
                    "raw": data,
                }
            except Exception as exc:
                logger.exception("Status query failed for %s: %s", contactor.name, exc)
                status_map[key] = {
                    "name": contactor.name,
                    "state": "UNKNOWN",
                    "error": str(exc),
                    "config": asdict(contactor),
                }
            finally:
                if device is not None:
                    try:
                        device.close()
                    except Exception:
                        pass
        return status_map
