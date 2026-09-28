from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.config import TemperatureProtectionSettings, VoltageProtectionSettings
from app.voltage_protection import VoltageProtectionMonitor


class VoltageProtectionTests(unittest.TestCase):
    def test_auto_start_disabled_event_is_logged_every_three_hours(self):
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

        with (
            patch(
                "app.voltage_protection.time.monotonic",
                side_effect=[100.0, 200.0, 10899.0, 10900.0],
            ),
            patch("app.voltage_protection.log_system_event") as log_event,
        ):
            for _ in range(4):
                monitor._maybe_auto_start(snapshot)

        self.assertEqual(log_event.call_count, 2)
        self.assertEqual(log_event.call_args.kwargs["reason"], "AUTO_START_DISABLED")


if __name__ == "__main__":
    unittest.main()
