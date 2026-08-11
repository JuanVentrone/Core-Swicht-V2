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
    port: str = "/dev/ttyUSB0"
    slave_address: int = 1
    baudrate: int = 9600
    bytesize: int = 8
    stopbits: int = 1
    parity: str = "N"
    timeout: float = 1.0
    poll_interval_seconds: float = 1.0
    reconnect_delay_seconds: float = 3.0


@dataclass(frozen=True)
class TemperatureModbusSettings(ModbusSettings):
    temperature_register: int = 0
    temperature_decimals: int = 1


@dataclass(frozen=True)
class TemperatureProtectionSettings:
    """Umbrales para apagado por temperatura alta (ver config/config.ini)."""

    enabled: bool
    max_temperature_c: float
    check_interval_seconds: float
