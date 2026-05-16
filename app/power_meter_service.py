from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

import minimalmodbus

logger = logging.getLogger("farm-control")


@dataclass
class PowerMetrics:
    voltage: float
    current: float
    active_power: float
    energy_kwh: float
    timestamp: str
    source: str


class PowerMeterService:
    def __init__(self) -> None:
        self.port = os.getenv("RS485_PORT", "/dev/ttyUSB0")
        self.slave_address = int(os.getenv("MODBUS_SLAVE_ADDRESS", "1"))
        self.baudrate = int(os.getenv("MODBUS_BAUDRATE", "9600"))
        self.bytesize = int(os.getenv("MODBUS_BYTESIZE", "8"))
        self.stopbits = int(os.getenv("MODBUS_STOPBITS", "1"))
        self.parity = os.getenv("MODBUS_PARITY", "N")
        self.timeout = float(os.getenv("MODBUS_TIMEOUT", "1.0"))

        self._lock = Lock()
        self._instrument = None

    def _get_instrument(self) -> minimalmodbus.Instrument:
        if self._instrument is None:
            instrument = minimalmodbus.Instrument(self.port, self.slave_address)
            instrument.serial.baudrate = self.baudrate
            instrument.serial.bytesize = self.bytesize
            instrument.serial.stopbits = self.stopbits
            instrument.serial.parity = self.parity
            instrument.serial.timeout = self.timeout
            instrument.mode = minimalmodbus.MODE_RTU
            instrument.clear_buffers_before_each_transaction = True
            self._instrument = instrument
        return self._instrument

    def _read(self, register: int, decimals: int) -> float:
        instrument = self._get_instrument()
        return float(instrument.read_register(register, decimals, functioncode=3))

    def read_metrics(self) -> dict:
        with self._lock:
            try:
                voltage = self._read(0, 1)
                current = self._read(1, 2)
                active_power = self._read(3, 0)
                energy_kwh = self._read(5, 2)
                return {
                    "success": True,
                    "data": PowerMetrics(
                        voltage=voltage,
                        current=current,
                        active_power=active_power,
                        energy_kwh=energy_kwh,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source="modbus_rtu",
                    ).__dict__,
                }
            except Exception as exc:  # broad by design for serial/device failures
                logger.exception("Power meter read failed: %s", exc)
                return {
                    "success": False,
                    "error": str(exc),
                    "data": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "modbus_rtu",
                }
