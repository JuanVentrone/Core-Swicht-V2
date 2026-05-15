from configparser import ConfigParser
from pathlib import Path

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
