import unittest
from datetime import datetime, time, date
from decimal import Decimal

from salary_tick.calculator import calculate_today, pay_for_overtime_seconds
from salary_tick.models import SalarySettings


def settings(expected=time(19, 15)):
    return SalarySettings(
        year=2026, month=11, monthly_salary=Decimal("10000"), workdays=Decimal("21"),
        overtime_multiplier=Decimal("1.5"), work_start=time(8, 15), lunch_start=time(11, 45),
        lunch_end=time(12, 45), work_end=time(17, 15), overtime_start=time(17, 45), expected_end=expected,
    )


class CalculatorTests(unittest.TestCase):
    def test_before_work_is_zero(self):
        result = calculate_today(datetime(2026, 11, 2, 8, 0), settings())
        self.assertEqual(result.total_work_seconds, 0)
        self.assertEqual(result.today_total_pay, Decimal("0"))

    def test_lunch_is_paused(self):
        before = calculate_today(datetime(2026, 11, 2, 11, 45), settings())
        during = calculate_today(datetime(2026, 11, 2, 12, 30), settings())
        self.assertEqual(before.total_work_seconds, during.total_work_seconds)
        self.assertEqual(before.today_total_pay, during.today_total_pay)

    def test_overtime_waiting_period_is_not_counted(self):
        at_end = calculate_today(datetime(2026, 11, 2, 17, 15), settings())
        waiting = calculate_today(datetime(2026, 11, 2, 17, 30), settings())
        self.assertEqual(at_end.total_work_seconds, waiting.total_work_seconds)
        self.assertEqual(waiting.overtime_work_seconds, 0)

    def test_expected_end_gives_nine_and_half_hours(self):
        result = calculate_today(datetime(2026, 11, 2, 19, 15), settings())
        self.assertEqual(result.normal_work_seconds, 8 * 3600)
        self.assertEqual(result.overtime_work_seconds, 90 * 60)
        self.assertEqual(result.total_work_seconds, 9 * 3600 + 30 * 60)

    def test_overtime_stops_at_expected_end(self):
        at_end = calculate_today(datetime(2026, 11, 2, 19, 15), settings())
        later = calculate_today(datetime(2026, 11, 2, 20, 0), settings())
        self.assertEqual(at_end.overtime_work_seconds, later.overtime_work_seconds)
        self.assertEqual(at_end.today_overtime_pay, later.today_overtime_pay)

    def test_stopwatch_preserves_subsecond_pay(self):
        first = calculate_today(datetime(2026, 11, 2, 9, 0, 0, 0), settings())
        second = calculate_today(datetime(2026, 11, 2, 9, 0, 0, 50000), settings())
        self.assertGreater(second.today_total_pay, first.today_total_pay)
        self.assertEqual(second.total_work_seconds, first.total_work_seconds)

    def test_non_current_month_does_not_calculate_today(self):
        old = settings()
        old = SalarySettings(
            year=2026, month=10, monthly_salary=old.monthly_salary, workdays=old.workdays,
            overtime_multiplier=old.overtime_multiplier, work_start=old.work_start,
            lunch_start=old.lunch_start, lunch_end=old.lunch_end, work_end=old.work_end,
            overtime_start=old.overtime_start, expected_end=old.expected_end,
        )
        result = calculate_today(datetime(2026, 11, 2, 10, 0), old)
        self.assertEqual(result.today_total_pay, Decimal("0"))
        self.assertEqual(result.status, "所选月份不是当前月份")


if __name__ == "__main__":
    unittest.main()
