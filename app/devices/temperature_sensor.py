from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import minimalmodbus

from app.config import TemperatureChannelConfig, TemperatureModbusSettings
from app.devices.base import BaseDevice

logger = logging.getLogger("farm-control")


@dataclass
class TemperatureSnapshot:
    temperature_c: float | None
    ambient_temperature_c: float | None = None
    channels: dict[str, float] | None = None
    timestamp: str = ""
    source: str = ""


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
        return float(instrument.read_register(register, decimals, functioncode=3, signed=True))

    def _get_channel_values(self) -> dict[str, float]:
        values: dict[str, float] = {}
        channels = self.settings.channels or []
        for channel in channels:
            if not channel.enabled:
                continue
            raw_value = self._read_register(channel.register, channel.decimals)
            values[channel.name] = raw_value
        return values

    def _read_snapshot(self) -> TemperatureSnapshot:
        channel_values = self._get_channel_values()
        primary_name = None
        primary_value = None

        if self.settings.channels:
            for channel in self.settings.channels:
                if channel.enabled:
                    primary_name = channel.name
                    primary_value = channel_values.get(channel.name)
                    break

        if primary_value is None and channel_values:
            primary_name, primary_value = next(iter(channel_values.items()))

        ambient_value = None
        for name, value in channel_values.items():
            if "ambiente" in name.lower() or name.lower() == "ambiente":
                ambient_value = value
                break

        if ambient_value is None:
            second_channel = None
            if self.settings.channels:
                for channel in self.settings.channels:
                    if channel.enabled and channel.name.lower() != (primary_name or "").lower():
                        second_channel = channel
                        break
            if second_channel is not None:
                ambient_value = channel_values.get(second_channel.name)

        return TemperatureSnapshot(
            temperature_c=primary_value,
            ambient_temperature_c=ambient_value,
            channels=channel_values,
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
