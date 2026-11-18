import unittest
from datetime import date

from salary_tick.calendar_service import is_legal_workday, month_workdays


class CalendarServiceTests(unittest.TestCase):
    def test_new_year_holiday(self):
        self.assertFalse(is_legal_workday(date(2026, 1, 1)))

    def test_makeup_sunday_is_workday(self):
        self.assertTrue(is_legal_workday(date(2026, 1, 4)))

    def test_normal_weekday(self):
        self.assertTrue(is_legal_workday(date(2026, 11, 2)))

    def test_month_has_positive_workdays(self):
        self.assertGreater(month_workdays(2026, 11), 0)


if __name__ == "__main__":
    unittest.main()
