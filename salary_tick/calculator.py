from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from .calendar_service import completed_workdays_before, is_legal_workday
from .models import CalculationResult, MonthResult, OvertimeRecord, SalarySettings

ZERO = Decimal("0")


def _elapsed_seconds(start: datetime, end: datetime) -> float:
    """Return sub-second precision for smooth stopwatch pay animation."""
    return max(0.0, (end - start).total_seconds())


def _whole_seconds(value: float) -> int:
    return max(0, int(value))


def standard_work_seconds(settings: SalarySettings, day: datetime) -> int:
    start = datetime.combine(day.date(), settings.work_start)
    lunch_start = datetime.combine(day.date(), settings.lunch_start)
    lunch_end = datetime.combine(day.date(), settings.lunch_end)
    end = datetime.combine(day.date(), settings.work_end)
    return _whole_seconds(_elapsed_seconds(start, lunch_start) + _elapsed_seconds(lunch_end, end))


def validate_settings(settings: SalarySettings) -> None:
    if settings.monthly_salary < ZERO:
        raise ValueError("月基本工资不能为负数")
    if settings.workdays <= ZERO:
        raise ValueError("月工作日必须大于0")
    if settings.overtime_multiplier < ZERO:
        raise ValueError("加班倍率不能为负数")
    if not (settings.work_start < settings.lunch_start < settings.lunch_end < settings.work_end):
        raise ValueError("时间顺序应为：上班 < 午休开始 < 午休结束 < 下班")
    if settings.overtime_start < settings.work_end:
        raise ValueError("加班起算时间不能早于正常下班时间")
    if settings.expected_end < settings.work_end:
        raise ValueError("今日预计下班时间不能早于正常下班时间")


def pay_for_overtime_seconds(seconds: int, settings: SalarySettings) -> Decimal:
    validate_settings(settings)
    standard = standard_work_seconds(settings, datetime(settings.year, settings.month, 1))
    daily_pay = settings.monthly_salary / settings.workdays
    second_rate = daily_pay / Decimal(standard)
    return Decimal(max(0, int(seconds))) * second_rate * settings.overtime_multiplier


def calculate_today(now: datetime, settings: SalarySettings) -> CalculationResult:
    validate_settings(settings)
    if (settings.year, settings.month) != (now.year, now.month):
        return CalculationResult(ZERO, ZERO, ZERO, 0, 0, 0, "所选月份不是当前月份", False)

    day = now.date()
    start = datetime.combine(day, settings.work_start)
    lunch_start = datetime.combine(day, settings.lunch_start)
    lunch_end = datetime.combine(day, settings.lunch_end)
    work_end = datetime.combine(day, settings.work_end)
    overtime_start = datetime.combine(day, settings.overtime_start)
    expected_end = datetime.combine(day, settings.expected_end)

    standard = standard_work_seconds(settings, now)
    daily_pay = settings.monthly_salary / settings.workdays
    second_rate = daily_pay / Decimal(standard)

    if not is_legal_workday(day):
        return CalculationResult(ZERO, ZERO, ZERO, 0, 0, 0, "今天不是法定工作日", False)
    if now <= start:
        return CalculationResult(ZERO, ZERO, ZERO, 0, 0, 0, "尚未上班", False)

    morning_exact = _elapsed_seconds(start, min(now, lunch_start))
    afternoon_exact = _elapsed_seconds(lunch_end, min(now, work_end)) if now > lunch_end else 0.0
    normal_exact = min(float(standard), morning_exact + afternoon_exact)
    overtime_exact = (
        _elapsed_seconds(overtime_start, min(now, expected_end))
        if now > overtime_start and expected_end > overtime_start else 0.0
    )

    base_pay = min(daily_pay, Decimal(str(normal_exact)) * second_rate)
    overtime_pay = Decimal(str(overtime_exact)) * second_rate * settings.overtime_multiplier

    if lunch_start <= now < lunch_end:
        status = "午休中，收入暂停累计"
    elif now <= work_end:
        status = "正常工作时间"
    elif now < overtime_start:
        status = f"加班休息时间，{overtime_start:%H:%M}开始计薪"
    elif now <= expected_end:
        status = f"加班中，预计{expected_end:%H:%M}结束"
    else:
        status = f"今日计算已于{expected_end:%H:%M}停止"

    normal_seconds = _whole_seconds(normal_exact)
    overtime_seconds = _whole_seconds(overtime_exact)
    return CalculationResult(
        today_base_pay=base_pay,
        today_overtime_pay=overtime_pay,
        today_total_pay=base_pay + overtime_pay,
        normal_work_seconds=normal_seconds,
        overtime_work_seconds=overtime_seconds,
        total_work_seconds=normal_seconds + overtime_seconds,
        status=status,
        reached_expected_end=now >= expected_end,
    )


def calculate_month(now: datetime, settings: SalarySettings, records: Iterable[OvertimeRecord], include_live_today: bool = False) -> MonthResult:
    validate_settings(settings)
    completed = completed_workdays_before(now.date(), settings.year, settings.month)
    daily_pay = settings.monthly_salary / settings.workdays
    filtered: list[OvertimeRecord] = []
    for record in records:
        if (record.record_date.year, record.record_date.month) != (settings.year, settings.month):
            continue
        if (not include_live_today and record.record_date == now.date() and record.source == "automatic" and now.time() < settings.expected_end):
            continue
        filtered.append(record)
    overtime_seconds = sum(record.overtime_seconds for record in filtered)
    overtime_pay = pay_for_overtime_seconds(overtime_seconds, settings) if overtime_seconds else ZERO
    base_pay = Decimal(completed) * daily_pay
    return MonthResult(base_pay, overtime_pay, base_pay + overtime_pay, completed, sum(r.overtime_seconds > 0 for r in filtered), overtime_seconds)
