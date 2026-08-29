from configparser import ConfigParser
from pathlib import Path

from app.config import (
    ModbusSettings,
    TemperatureChannelConfig,
    TemperatureModbusSettings,
    TemperatureProtectionSettings,
    VoltageProtectionSettings,
)
from app.models import Contactor


CONFIG_DIR = Path("config")
ALARM_CONFIG_DIR = CONFIG_DIR / "device_alarm"


def load_contactors(config_dir: Path = CONFIG_DIR) -> dict[str, Contactor]:
    contactors: dict[str, Contactor] = {}
    for ini_file in sorted(config_dir.glob("*.ini")):
        if ini_file.stem.lower().endswith("example"):
            continue
        parser = ConfigParser()
        parser.read(ini_file, encoding="utf-8")
        if "DEVICE" not in parser:
            continue

        section = parser["DEVICE"]
        contactor = Contactor(
            name=section.get("name", ini_file.stem),
            id=section.get("id", ""),
            ip=section.get("ip", ""),
            key=section.get("key", ""),
            version=section.get("version", "3.4"),
        )
        contactors[ini_file.stem.upper()] = contactor
    return contactors


def load_alarm_devices(config_dir: Path = ALARM_CONFIG_DIR) -> dict[str, Contactor]:
    alarm_devices: dict[str, Contactor] = {}
    for ini_file in sorted(config_dir.glob("*.ini")):
        parser = ConfigParser()
        parser.read(ini_file, encoding="utf-8")
        if "DEVICE" not in parser:
            continue

        section = parser["DEVICE"]
        device = Contactor(
            name=section.get("name", ini_file.stem),
            id=section.get("id", ""),
            ip=section.get("ip", ""),
            key=section.get("key", ""),
            version=section.get("version", "3.4"),
        )
        alarm_devices[ini_file.stem.upper()] = device
    return alarm_devices


def load_voltage_protection_settings(
    config_dir: Path = CONFIG_DIR,
) -> VoltageProtectionSettings:
    """Lee config/config.ini sección [VOLTAGE_PROTECTION]. Si falta el archivo o la sección, desactivado."""
    path = config_dir / "config.ini"
    default = VoltageProtectionSettings(
        enabled=False,
        min_volts=218.0,
        max_volts=253.0,
        check_interval_seconds=2.0,
        startup_read_timeout_seconds=90.0,
        auto_start_enabled=True,
        auto_start_min_volts=220.0,
        auto_start_max_volts=245.0,
        auto_start_stable_seconds=180.0,
    )
    if not path.is_file():
        return default

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if "VOLTAGE_PROTECTION" not in parser:
        return default

    sec = parser["VOLTAGE_PROTECTION"]
    return VoltageProtectionSettings(
        enabled=sec.getboolean("enabled", fallback=False),
        min_volts=sec.getfloat("min_volts", fallback=default.min_volts),
        max_volts=sec.getfloat("max_volts", fallback=default.max_volts),
        check_interval_seconds=sec.getfloat(
            "check_interval_seconds",
            fallback=default.check_interval_seconds,
        ),
        startup_read_timeout_seconds=sec.getfloat(
            "startup_read_timeout_seconds",
            fallback=default.startup_read_timeout_seconds,
        ),
        auto_start_enabled=sec.getboolean("auto_start_enabled", fallback=default.auto_start_enabled),
        auto_start_min_volts=sec.getfloat(
            "auto_start_min_volts",
            fallback=default.auto_start_min_volts,
        ),
        auto_start_max_volts=sec.getfloat(
            "auto_start_max_volts",
            fallback=default.auto_start_max_volts,
        ),
        auto_start_stable_seconds=sec.getfloat(
            "auto_start_stable_seconds",
            fallback=default.auto_start_stable_seconds,
        ),
    )


def load_modbus_settings(
    config_dir: Path = CONFIG_DIR,
    section: str = "MODBUS_VOLTAGE",
    default_port: str = "/dev/ttyUSB0",
    config_filename: str = "modbus_voltage.ini",
) -> ModbusSettings:
    path = config_dir / config_filename
    if not path.is_file():
        legacy_path = config_dir / "config.ini"
        path = legacy_path if legacy_path.is_file() else path
    settings = ModbusSettings(port=default_port)
    if not path.is_file():
        return settings

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if section not in parser:
        return settings

    sec = parser[section]
    return ModbusSettings(
        port=sec.get("port", fallback=default_port),
        slave_address=sec.getint("slave_address", fallback=settings.slave_address),
        baudrate=sec.getint("baudrate", fallback=settings.baudrate),
        bytesize=sec.getint("bytesize", fallback=settings.bytesize),
        stopbits=sec.getint("stopbits", fallback=settings.stopbits),
        parity=sec.get("parity", fallback=settings.parity),
        timeout=sec.getfloat("timeout", fallback=settings.timeout),
        poll_interval_seconds=sec.getfloat(
            "poll_interval_seconds",
            fallback=settings.poll_interval_seconds,
        ),
        reconnect_delay_seconds=sec.getfloat(
            "reconnect_delay_seconds",
            fallback=settings.reconnect_delay_seconds,
        ),
    )


def _default_temperature_channels() -> list[TemperatureChannelConfig]:
    return [
        TemperatureChannelConfig(name="Transformador", register=0, decimals=1, enabled=True),
        TemperatureChannelConfig(name="Ambiente", register=1, decimals=1, enabled=True),
        TemperatureChannelConfig(name="Canal 3", register=2, decimals=1, enabled=False),
        TemperatureChannelConfig(name="Canal 4", register=3, decimals=1, enabled=False),
    ]


def _load_temperature_channels(parser: ConfigParser) -> list[TemperatureChannelConfig]:
    default_channels = _default_temperature_channels()
    channels: list[TemperatureChannelConfig] = []

    for index in range(1, 5):
        section_name = f"CHANNEL_{index}"
        if section_name not in parser:
            if index <= len(default_channels):
                channels.append(default_channels[index - 1])
            continue

        sec = parser[section_name]
        enabled = sec.getboolean("enabled", fallback=True)
        if not enabled:
            channels.append(
                TemperatureChannelConfig(
                    name=sec.get("name", fallback=f"Canal {index}"),
                    register=sec.getint("register", fallback=(index - 1)),
                    decimals=sec.getint("decimals", fallback=1),
                    enabled=False,
                )
            )
            continue

        channels.append(
            TemperatureChannelConfig(
                name=sec.get("name", fallback=f"Canal {index}"),
                register=sec.getint("register", fallback=(index - 1)),
                decimals=sec.getint("decimals", fallback=1),
                enabled=True,
            )
        )

    if channels:
        return channels
    return default_channels


def load_temperature_modbus_settings(
    config_dir: Path = CONFIG_DIR,
    section: str = "MODBUS_TEMPERATURE",
    default_port: str = "/dev/ttyUSB1",
    config_filename: str = "modbus_temperature.ini",
) -> TemperatureModbusSettings:
    path = config_dir / config_filename
    if not path.is_file():
        legacy_path = config_dir / "config.ini"
        path = legacy_path if legacy_path.is_file() else path
    default = TemperatureModbusSettings(port=default_port)
    if not path.is_file():
        return TemperatureModbusSettings(
            port=default_port,
            channels=_default_temperature_channels(),
        )

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if section not in parser:
        return TemperatureModbusSettings(
            port=default_port,
            channels=_default_temperature_channels(),
        )

    sec = parser[section]
    legacy_register = sec.getint("temperature_register", fallback=default.temperature_register)
    legacy_decimals = sec.getint("temperature_decimals", fallback=default.temperature_decimals)
    channels = _load_temperature_channels(parser)

    if not channels:
        channels = [
            TemperatureChannelConfig(
                name="Transformador",
                register=legacy_register,
                decimals=legacy_decimals,
                enabled=True,
            )
        ]

    return TemperatureModbusSettings(
        port=sec.get("port", fallback=default.port),
        slave_address=sec.getint("slave_address", fallback=default.slave_address),
        baudrate=sec.getint("baudrate", fallback=default.baudrate),
        bytesize=sec.getint("bytesize", fallback=default.bytesize),
        stopbits=sec.getint("stopbits", fallback=default.stopbits),
        parity=sec.get("parity", fallback=default.parity),
        timeout=sec.getfloat("timeout", fallback=default.timeout),
        poll_interval_seconds=sec.getfloat(
            "poll_interval_seconds",
            fallback=default.poll_interval_seconds,
        ),
        reconnect_delay_seconds=sec.getfloat(
            "reconnect_delay_seconds",
            fallback=default.reconnect_delay_seconds,
        ),
        temperature_register=legacy_register,
        temperature_decimals=legacy_decimals,
        channels=channels,
    )


def load_temperature_protection_settings(
    config_dir: Path = CONFIG_DIR,
) -> TemperatureProtectionSettings:
    """Lee config/config.ini sección [TEMPERATURE_PROTECTION]."""
    path = config_dir / "config.ini"
    default = TemperatureProtectionSettings(
        enabled=False,
        max_temperature_c=80.0,
        check_interval_seconds=4.0,
    )
    if not path.is_file():
        return default

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if "TEMPERATURE_PROTECTION" not in parser:
        return default

    sec = parser["TEMPERATURE_PROTECTION"]
    return TemperatureProtectionSettings(
        enabled=sec.getboolean("enabled", fallback=False),
        max_temperature_c=sec.getfloat("max_temperature_c", fallback=default.max_temperature_c),
        check_interval_seconds=sec.getfloat(
            "check_interval_seconds",
            fallback=default.check_interval_seconds,
        ),
    )
