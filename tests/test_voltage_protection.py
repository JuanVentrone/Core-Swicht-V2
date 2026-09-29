from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.config import TemperatureProtectionSettings, VoltageProtectionSettings
from app.voltage_protection import VoltageProtectionMonitor


class VoltageProtectionTests(unittest.TestCase):
    def test_auto_start_disabled_does_not_log_system_event(self):
        settings = VoltageProtectionSettings(
            enabled=True,
            min_volts=218.0,
            max_volts=253.0,
            check_interval_seconds=2.0,
            startup_read_timeout_seconds=90.0,
            auto_start_enabled=False,
            auto_start_min_volts=220.0,
            auto_start_max_volts=245.0,
            auto_start_stable_seconds=180.0,
        )
        controller = Mock(manual_shutdown=False)
        monitor = VoltageProtectionMonitor(
            None,
            None,
            controller,
            settings,
            TemperatureProtectionSettings(
                enabled=False,
                max_temperature_c=80.0,
                check_interval_seconds=4.0,
            ),
        )
        snapshot = SimpleNamespace(v_l1=227.8, v_l2=225.8, v_l3=224.4)

        with patch("app.voltage_protection.log_system_event") as log_event:
            for _ in range(4):
                monitor._maybe_auto_start(snapshot)

        log_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
