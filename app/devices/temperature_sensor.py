from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import minimalmodbus

from app.config import TemperatureModbusSettings
from app.devices.base import BaseDevice

logger = logging.getLogger("farm-control")


@dataclass
class TemperatureSnapshot:
    temperature_c: float | None
    timestamp: str
    source: str


class TemperatureSensorDevice(BaseDevice):
    def __init__(self, settings: TemperatureModbusSettings) -> None:
        super().__init__(device_id="temperature-sensor", name="Temperature Sensor")
        self.settings = settings
        self._instrument: minimalmodbus.Instrument | None = None
        self._lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_snapshot: TemperatureSnapshot | None = None

    @property
    def last_snapshot(self) -> TemperatureSnapshot | None:
        with self._lock:
            return self._last_snapshot

    def initialize(self) -> None:
        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True,
            name="temperature-modbus-polling-thread",
        )
        self._reader_thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2)
        self._close_instrument()
        self._healthy = False

    def _build_instrument(self) -> minimalmodbus.Instrument:
        instrument = minimalmodbus.Instrument(self.settings.port, self.settings.slave_address)
        instrument.serial.baudrate = self.settings.baudrate
        instrument.serial.bytesize = self.settings.bytesize
        instrument.serial.stopbits = self.settings.stopbits
        instrument.serial.parity = self.settings.parity
        instrument.serial.timeout = self.settings.timeout
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.clear_buffers_before_each_transaction = True
        return instrument

    def _ensure_instrument(self) -> minimalmodbus.Instrument:
        if self._instrument is None:
            self._instrument = self._build_instrument()
        return self._instrument

    def _close_instrument(self) -> None:
        if self._instrument is None:
            return
        try:
            self._instrument.serial.close()
        except Exception:
            pass
        self._instrument = None

    def _read_register(self, register: int, decimals: int) -> float:
        instrument = self._ensure_instrument()
        return float(instrument.read_register(register, decimals, functioncode=3))

    def _read_snapshot(self) -> TemperatureSnapshot:
        register = self.settings.temperature_register
        value = self._read_register(register, self.settings.temperature_decimals)
        return TemperatureSnapshot(
            temperature_c=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="modbus_rtu_rs485_temperature",
        )

    def _polling_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                snapshot = self._read_snapshot()
                with self._lock:
                    self._last_snapshot = snapshot
                self._healthy = True
                self._last_error = ""
                time.sleep(self.settings.poll_interval_seconds)
            except Exception as exc:  # broad by design for serial/device failures
                logger.warning("Temperature RS485 read failed, attempting reconnect: %s", exc)
                self._healthy = False
                self._last_error = str(exc)
                self._close_instrument()
                time.sleep(self.settings.reconnect_delay_seconds)
