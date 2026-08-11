from __future__ import annotations

import logging
import threading
import time

from app.config import TemperatureProtectionSettings, VoltageProtectionSettings
from app.devices.industrial_multimeter import IndustrialMultimeterDevice, MultimeterSnapshot
from app.devices.temperature_sensor import TemperatureSensorDevice
from app.services import FarmController

logger = logging.getLogger("farm-control")


class VoltageProtectionMonitor:
    """Apaga C1–C3 si L1, L2 o L3 salen del rango [min_volts, max_volts].
    Tras voltaje estable en [auto_start_min, auto_start_max] durante auto_start_stable_seconds,
    solicita encendido secuencial automático."""

    def __init__(
        self,
        multimeter: IndustrialMultimeterDevice,
        temperature_sensor: TemperatureSensorDevice,
        controller: FarmController,
        settings: VoltageProtectionSettings,
        temperature_settings: TemperatureProtectionSettings,
    ) -> None:
        self._multimeter = multimeter
        self._temperature_sensor = temperature_sensor
        self._controller = controller
        self._settings = settings
        self._temperature_settings = temperature_settings
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._tripped = False
        self._temperature_tripped = False
        self._stable_since: float | None = None

    def run_startup_gate(self) -> None:
        """Tras iniciar solo el medidor: exige primer snapshot; si voltaje fuera de rango → apagado."""
        if not self._settings.enabled:
            return

        timeout = max(5.0, self._settings.startup_read_timeout_seconds)
        deadline = time.monotonic() + timeout
        poll = 0.25

        while time.monotonic() < deadline:
            voltage_snap = self._multimeter.last_snapshot
            temperature_snap = self._temperature_sensor.last_snapshot
            voltage_ready = voltage_snap is not None or not self._settings.enabled
            temperature_ready = temperature_snap is not None or not self._temperature_settings.enabled

            if voltage_ready and temperature_ready:
                if self._settings.enabled and voltage_snap is not None and self._any_line_trip(voltage_snap):
                    logger.error(
                        "Arranque: voltaje fuera de rango permitido (%.1f–%.1f V): "
                        "L1=%.1f L2=%.1f L3=%.1f → apagado general",
                        self._settings.min_volts,
                        self._settings.max_volts,
                        voltage_snap.v_l1,
                        voltage_snap.v_l2,
                        voltage_snap.v_l3,
                    )
                    self._controller.General_Switch_System(False)
                    return

                if self._temperature_settings.enabled and temperature_snap is not None:
                    if self._is_temperature_trip(temperature_snap):
                        logger.error(
                            "Arranque: temperatura excede el máximo permitido (%.1f °C): %.1f °C → apagado general",
                            self._temperature_settings.max_temperature_c,
                            temperature_snap.temperature_c,
                        )
                        self._controller.General_Switch_System(False)
                        return

                if self._settings.enabled and voltage_snap is not None:
                    logger.info(
                        "Arranque: voltaje OK para operar (%.1f–%.1f V): "
                        "L1=%.1f L2=%.1f L3=%.1f",
                        self._settings.min_volts,
                        self._settings.max_volts,
                        voltage_snap.v_l1,
                        voltage_snap.v_l2,
                        voltage_snap.v_l3,
                    )
                if self._temperature_settings.enabled and temperature_snap is not None:
                    logger.info(
                        "Arranque: temperatura OK para operar (%.1f °C)",
                        temperature_snap.temperature_c,
                    )
                return

            time.sleep(poll)

        logger.error(
            "Arranque: sin lectura del medidor en %.0f s; apagado preventivo",
            timeout,
        )
        self._controller.General_Switch_System(False)

    def start(self) -> None:
        if not self._settings.enabled and not self._temperature_settings.enabled:
            logger.info("Protection monitor disabled (config.ini)")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="protection-monitor",
        )
        self._thread.start()
        logger.info(
            "Voltage protection enabled: trip %.1f–%.1f V, auto-start band %.1f–%.1f V "
            "(%.0f s estable), interval %.1f s",
            self._settings.min_volts,
            self._settings.max_volts,
            self._settings.auto_start_min_volts,
            self._settings.auto_start_max_volts,
            self._settings.auto_start_stable_seconds,
            self._settings.check_interval_seconds,
        )
        if self._temperature_settings.enabled:
            logger.info(
                "Temperature protection enabled: max %.1f °C, interval %.1f s",
                self._temperature_settings.max_temperature_c,
                self._temperature_settings.check_interval_seconds,
            )

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None

    def _line_out_of_trip_range(self, value: float) -> bool:
        return value < self._settings.min_volts or value > self._settings.max_volts

    def _any_line_trip(self, snap: MultimeterSnapshot) -> bool:
        return any(
            self._line_out_of_trip_range(v) for v in (snap.v_l1, snap.v_l2, snap.v_l3)
        )

    def _all_in_auto_start_band(self, snap: MultimeterSnapshot) -> bool:
        lo, hi = self._settings.auto_start_min_volts, self._settings.auto_start_max_volts
        return all(lo <= v <= hi for v in (snap.v_l1, snap.v_l2, snap.v_l3))

    def _maybe_auto_start(self, snapshot: MultimeterSnapshot) -> None:
        if not self._settings.auto_start_enabled:
            self._stable_since = None
            return

        if not self._all_in_auto_start_band(snapshot):
            self._stable_since = None
            return

        now = time.monotonic()
        if self._stable_since is None:
            self._stable_since = now
            return

        elapsed = now - self._stable_since
        need = max(1.0, self._settings.auto_start_stable_seconds)
        if elapsed < need:
            return

        result = self._controller.General_Switch_System(True)
        msg = (result.get("message") or "").lower()
        if result.get("accepted"):
            self._stable_since = None
            logger.info(
                "Auto-arranque: %.0f s estable en %.1f–%.1f V (L1=%.1f L2=%.1f L3=%.1f) → encendido secuencial",
                elapsed,
                self._settings.auto_start_min_volts,
                self._settings.auto_start_max_volts,
                snapshot.v_l1,
                snapshot.v_l2,
                snapshot.v_l3,
            )
        elif "already running" in msg:
            self._stable_since = time.monotonic()
        else:
            self._stable_since = None
            logger.debug("Auto-arranque omitido: %s", result.get("message", result))

    def _is_temperature_trip(self, snapshot: object) -> bool:
        if not self._temperature_settings.enabled:
            return False
        temperature = getattr(snapshot, "temperature_c", None)
        if temperature is None:
            return False
        return temperature > self._temperature_settings.max_temperature_c

    def _log_temperature_trip(self, temperature: float) -> None:
        logger.error(
            "Temperatura excede el máximo permitido (%.1f °C): %.1f °C → apagado general",
            self._temperature_settings.max_temperature_c,
            temperature,
        )

    def _loop(self) -> None:
        interval = max(
            0.5,
            self._settings.check_interval_seconds,
            self._temperature_settings.check_interval_seconds,
        )
        while not self._stop.is_set():
            voltage_snapshot = self._multimeter.last_snapshot
            temperature_snapshot = self._temperature_sensor.last_snapshot

            if voltage_snapshot is None and self._settings.enabled:
                time.sleep(interval)
                continue
            if temperature_snapshot is None and self._temperature_settings.enabled:
                time.sleep(interval)
                continue

            temperature_trip = self._is_temperature_trip(temperature_snapshot)
            voltage_bad = (
                self._line_out_of_trip_range(voltage_snapshot.v_l1),
                self._line_out_of_trip_range(voltage_snapshot.v_l2),
                self._line_out_of_trip_range(voltage_snapshot.v_l3),
            ) if voltage_snapshot is not None else (False, False, False)

            if any(voltage_bad):
                lines = ["L1" if voltage_bad[0] else None, "L2" if voltage_bad[1] else None, "L3" if voltage_bad[2] else None]
                fault_lines = [x for x in lines if x]
                self._stable_since = None
                if not self._tripped:
                    logger.error(
                        "Voltaje fuera de rango (%.1f–%.1f V): L1=%.1f L2=%.1f L3=%.1f → apagado general",
                        self._settings.min_volts,
                        self._settings.max_volts,
                        voltage_snapshot.v_l1,
                        voltage_snapshot.v_l2,
                        voltage_snapshot.v_l3,
                    )
                    result = self._controller.General_Switch_System(False)
                    logger.warning("Protección voltaje: apagado ejecutado: %s", result)
                    self._tripped = True
                else:
                    logger.debug(
                        "Voltaje sigue fuera de rango (%s); ya en trip. L1=%.1f L2=%.1f L3=%.1f",
                        ", ".join(fault_lines),
                        voltage_snapshot.v_l1,
                        voltage_snapshot.v_l2,
                        voltage_snapshot.v_l3,
                    )
            elif temperature_trip:
                self._stable_since = None
                if not self._temperature_tripped:
                    temperature = temperature_snapshot.temperature_c if temperature_snapshot is not None else float('nan')
                    self._log_temperature_trip(temperature)
                    result = self._controller.General_Switch_System(False)
                    logger.warning("Protección temperatura: apagado ejecutado: %s", result)
                    self._temperature_tripped = True
                else:
                    temperature = temperature_snapshot.temperature_c if temperature_snapshot is not None else float('nan')
                    logger.debug(
                        "Temperatura sigue fuera de rango (%.1f °C); ya en trip",
                        temperature,
                    )
            else:
                if self._tripped and voltage_snapshot is not None:
                    logger.info(
                        "Voltaje normalizado (L1=%.1f L2=%.1f L3=%.1f V); listo para vigilancia y auto-arranque",
                        voltage_snapshot.v_l1,
                        voltage_snapshot.v_l2,
                        voltage_snapshot.v_l3,
                    )
                if self._temperature_tripped and temperature_snapshot is not None:
                    logger.info(
                        "Temperatura normalizada (%.1f °C); listo para vigilancia",
                        temperature_snapshot.temperature_c,
                    )
                self._tripped = False
                self._temperature_tripped = False
                if voltage_snapshot is not None:
                    self._maybe_auto_start(voltage_snapshot)

            time.sleep(interval)
