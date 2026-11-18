import unittest

from salary_tick.display_service import DisplayArea
from salary_tick.window_state_rules import (
    float_window_is_mandatory,
    floating_menu_position,
    popup_size,
)


class WindowStateRuleTests(unittest.TestCase):
    def test_float_window_is_always_required(self):
        self.assertTrue(float_window_is_mandatory())

    def test_normal_screen_settings_size_is_compact(self):
        self.assertEqual(popup_size(1366, 768), (680, 500))

    def test_small_screen_settings_size_fits_available_area(self):
        self.assertEqual(popup_size(640, 480), (560, 400))

    def test_minimum_fallback(self):
        self.assertEqual(popup_size(300, 300), (540, 400))

    def test_left_monitor_menu_stays_on_left_monitor(self):
        left = DisplayArea(-1920, 0, 0, 1040)
        x, y = floating_menu_position(-1800, 850, 300, 102, 190, 300, left)
        self.assertEqual((x, y), (-1492, 732))

    def test_right_monitor_menu_stays_on_right_monitor(self):
        right = DisplayArea(1920, -200, 3840, 880)
        x, y = floating_menu_position(2500, 700, 300, 102, 190, 300, right)
        self.assertEqual((x, y), (2808, 572))

    def test_menu_opens_left_when_near_monitor_right_edge(self):
        area = DisplayArea(0, 0, 1920, 1040)
        x, _ = floating_menu_position(1650, 600, 300, 102, 190, 300, area)
        self.assertEqual(x, 1452)

    def test_bottom_left_menu_expands_upward(self):
        area = DisplayArea(0, 0, 1920, 1040)
        _, y = floating_menu_position(20, 930, 300, 102, 190, 300, area)
        self.assertEqual(y, 732)

    def test_menu_keeps_monitor_top_margin(self):
        area = DisplayArea(1920, -200, 3840, 880)
        _, y = floating_menu_position(2000, -190, 300, 102, 190, 300, area)
        self.assertEqual(y, -192)


if __name__ == "__main__":
    unittest.main()
