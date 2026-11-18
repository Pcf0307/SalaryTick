import unittest

from salary_tick.display_service import (
    DisplayArea,
    area_for_window,
    restore_visible_position,
    window_is_visible,
)


PRIMARY = DisplayArea(0, 0, 1920, 1040, True)
LEFT = DisplayArea(-1920, 0, 0, 1040, False)
RIGHT = DisplayArea(1920, -200, 3840, 880, False)
DISPLAYS = [LEFT, PRIMARY, RIGHT]


class DisplayServiceTests(unittest.TestCase):
    def test_negative_coordinate_on_left_monitor_is_valid(self):
        self.assertTrue(window_is_visible(-1800, 800, 300, 102, DISPLAYS))

    def test_right_monitor_position_is_valid(self):
        self.assertTrue(window_is_visible(2500, 600, 300, 102, DISPLAYS))

    def test_window_center_selects_left_monitor(self):
        self.assertEqual(area_for_window(-1800, 800, 300, 102, DISPLAYS), LEFT)

    def test_window_center_selects_right_monitor_with_negative_top(self):
        self.assertEqual(area_for_window(2500, -100, 300, 102, DISPLAYS), RIGHT)

    def test_valid_saved_secondary_position_is_preserved(self):
        self.assertEqual(
            restore_visible_position(-1800, 800, 300, 102, DISPLAYS),
            (-1800, 800),
        )

    def test_missing_monitor_position_recovers_to_primary_bottom_left(self):
        x, y = restore_visible_position(5000, 2000, 300, 102, DISPLAYS)
        self.assertEqual((x, y), (20, 918))

    def test_partially_visible_window_is_preserved(self):
        self.assertEqual(
            restore_visible_position(-40, 900, 300, 102, [PRIMARY]),
            (-40, 900),
        )

    def test_tiny_visible_sliver_is_recovered(self):
        self.assertEqual(
            restore_visible_position(-280, 900, 300, 102, [PRIMARY]),
            (20, 918),
        )


if __name__ == "__main__":
    unittest.main()
