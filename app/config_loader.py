from configparser import ConfigParser
from pathlib import Path

from app.config import VoltageProtectionSettings
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
