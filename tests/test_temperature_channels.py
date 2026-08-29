import tempfile
import unittest
from pathlib import Path

from app.config_loader import load_temperature_modbus_settings


class TemperatureChannelConfigTest(unittest.TestCase):
    def test_load_temperature_channels_from_ini(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "config.ini").write_text(
                """
[MODBUS_TEMPERATURE]
port = /dev/serial/by-path/test-port
autobrate = 9600
slave_address = 1
baudrate = 9600
bytesize = 8
stopbits = 1
parity = N
timeout = 1.0
poll_interval_seconds = 2.0
reconnect_delay_seconds = 3.0

[CHANNEL_1]
name = Transformador
register = 0
decimals = 1
enabled = true

[CHANNEL_2]
name = Ambiente
register = 1
decimals = 1
enabled = true

[CHANNEL_3]
name = Canal 3
register = 2
decimals = 1
enabled = false

[CHANNEL_4]
name = Canal 4
register = 3
decimals = 1
enabled = false
""".strip(),
                encoding="utf-8",
            )

            settings = load_temperature_modbus_settings(config_dir=config_dir)

            self.assertEqual(len(settings.channels), 4)
            self.assertEqual(settings.channels[0].name, "Transformador")
            self.assertEqual(settings.channels[1].name, "Ambiente")
            self.assertFalse(settings.channels[2].enabled)
            self.assertEqual(settings.channels[3].register, 3)


if __name__ == "__main__":
    unittest.main()
