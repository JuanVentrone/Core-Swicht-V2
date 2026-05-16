from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoltageProtectionSettings:
    """Umbrales para apagado por voltaje en L1–L3 (ver config/config.ini)."""

    enabled: bool
    min_volts: float
    max_volts: float
    check_interval_seconds: float
    #: Espera máxima (s) al primer snapshot Modbus en el arranque antes de apagar por precaución.
    startup_read_timeout_seconds: float
    #: Tras voltaje estable en [auto_start_min, auto_start_max], encendido secuencial automático.
    auto_start_enabled: bool
    auto_start_min_volts: float
    auto_start_max_volts: float
    auto_start_stable_seconds: float


@dataclass(frozen=True)
class ModbusSettings:
    port: str = os.getenv("RS485_PORT", "/dev/ttyUSB0")
    slave_address: int = int(os.getenv("MODBUS_SLAVE_ADDRESS", "1"))
    baudrate: int = int(os.getenv("MODBUS_BAUDRATE", "9600"))
    bytesize: int = int(os.getenv("MODBUS_BYTESIZE", "8"))
    stopbits: int = int(os.getenv("MODBUS_STOPBITS", "1"))
    parity: str = os.getenv("MODBUS_PARITY", "N")
    timeout: float = float(os.getenv("MODBUS_TIMEOUT", "1.0"))
    poll_interval_seconds: float = float(os.getenv("MODBUS_POLL_INTERVAL_SECONDS", "1.0"))
    reconnect_delay_seconds: float = float(os.getenv("MODBUS_RECONNECT_DELAY_SECONDS", "3.0"))
