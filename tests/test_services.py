from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.services import FarmController


class FarmControllerManualShutdownTests(unittest.TestCase):
    def test_automatic_general_on_cannot_clear_manual_shutdown(self):
        controller = FarmController({})
        controller._set_manual_shutdown()

        with patch("app.services.log_system_event"):
            result = controller.General_Switch_System(True, manual=False)

        self.assertFalse(result["accepted"])
        self.assertTrue(controller.manual_shutdown)

    def test_manual_general_on_clears_manual_shutdown(self):
        controller = FarmController({})
        controller._set_manual_shutdown()

        with patch("app.services.log_system_event"):
            result = controller.General_Switch_System(True, manual=True)
        controller._switch_thread.join(timeout=1)

        self.assertTrue(result["accepted"])
        self.assertFalse(controller.manual_shutdown)

    def test_individual_contactor_on_is_blocked_by_manual_shutdown(self):
        contactor = SimpleNamespace(name="C1", version="3.4")
        controller = FarmController({"C1": contactor})
        controller._set_manual_shutdown()

        result = controller.ctr_contactor(contactor, True)

        self.assertFalse(result["success"])
        self.assertTrue(controller.manual_shutdown)

    def test_manual_off_sets_lock_and_cancels_sequential_start(self):
        controller = FarmController({})

        with patch("app.services.log_system_event"):
            controller.General_Switch_System(False, manual=True)

        self.assertTrue(controller.manual_shutdown)
        self.assertTrue(controller._switch_cancel.is_set())

    def test_cancelled_sequential_start_does_not_switch_next_contactor(self):
        contactors = {
            key: SimpleNamespace(name=key, version="3.4")
            for key in ("C1", "C2", "C3")
        }
        controller = FarmController(contactors)
        switch_calls = []

        def cancel_during_delay(_timeout):
            controller._switch_cancel.set()
            return True

        with (
            patch.object(
                controller,
                "_perform_contactor_switch",
                side_effect=lambda contactor, state: switch_calls.append((contactor.name, state))
                or {"success": True},
            ),
            patch.object(controller._switch_cancel, "wait", side_effect=cancel_during_delay),
        ):
            controller._run_sequential_on()

        self.assertEqual(switch_calls, [("C1", True)])


if __name__ == "__main__":
    unittest.main()