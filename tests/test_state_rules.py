import unittest

from salary_tick.state_rules import normalize_amount_visibility, normalize_expected_end
from salary_tick.calendar_service import month_workdays


class StateRuleTests(unittest.TestCase):
    def test_auto_workdays_are_available_for_selected_month(self):
        self.assertGreater(month_workdays(2026, 11), 0)
        self.assertGreater(month_workdays(2026, 12), 0)

    def test_expected_end_is_clamped_to_later_work_end(self):
        self.assertEqual(normalize_expected_end("18:00", "17:15"), "18:00")

    def test_later_expected_end_is_preserved(self):
        self.assertEqual(normalize_expected_end("17:15", "19:15"), "19:15")

    def test_manual_privacy_forces_float_amount_hidden(self):
        self.assertFalse(normalize_amount_visibility("手动切换", True))

    def test_always_hidden_forces_float_amount_hidden(self):
        self.assertFalse(normalize_amount_visibility("始终隐藏", True))

    def test_direct_display_can_restore_saved_float_state(self):
        self.assertTrue(normalize_amount_visibility("直接显示", True))
        self.assertFalse(normalize_amount_visibility("直接显示", False))


if __name__ == "__main__":
    unittest.main()
