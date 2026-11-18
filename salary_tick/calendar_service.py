from __future__ import annotations

import calendar
from datetime import date

HOLIDAY_CONFIG = {
    2026: {
        "holidays": {
            date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
            *{date(2026, 2, day) for day in range(15, 24)},
            date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),
            *{date(2026, 5, day) for day in range(1, 6)},
            date(2026, 6, 19), date(2026, 6, 20), date(2026, 6, 21),
            date(2026, 9, 25), date(2026, 9, 26), date(2026, 9, 27),
            *{date(2026, 10, day) for day in range(1, 8)},
        },
        "makeup": {
            date(2026, 1, 4), date(2026, 2, 14), date(2026, 2, 28),
            date(2026, 5, 9), date(2026, 9, 20), date(2026, 10, 10),
        },
    }
}


def has_official_calendar(year: int) -> bool:
    return year in HOLIDAY_CONFIG


def is_legal_workday(day: date) -> bool:
    config = HOLIDAY_CONFIG.get(day.year)
    if config:
        if day in config["makeup"]:
            return True
        if day in config["holidays"]:
            return False
    return day.weekday() < 5


def month_workdays(year: int, month: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    return sum(is_legal_workday(date(year, month, day)) for day in range(1, last_day + 1))


def completed_workdays_before(target: date, year: int, month: int) -> int:
    if (year, month) < (target.year, target.month):
        return month_workdays(year, month)
    if (year, month) > (target.year, target.month):
        return 0
    return sum(is_legal_workday(date(year, month, day)) for day in range(1, target.day))
