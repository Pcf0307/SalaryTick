from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, time
from decimal import Decimal
from typing import Literal

RecordSource = Literal["automatic", "manual", "manual_override"]


@dataclass(frozen=True)
class SalarySettings:
    year: int
    month: int
    monthly_salary: Decimal
    workdays: Decimal
    overtime_multiplier: Decimal
    work_start: time
    lunch_start: time
    lunch_end: time
    work_end: time
    overtime_start: time
    expected_end: time


@dataclass(frozen=True)
class CalculationResult:
    today_base_pay: Decimal
    today_overtime_pay: Decimal
    today_total_pay: Decimal
    normal_work_seconds: int
    overtime_work_seconds: int
    total_work_seconds: int
    status: str
    reached_expected_end: bool


@dataclass(frozen=True)
class MonthResult:
    base_pay: Decimal
    overtime_pay: Decimal
    total_pay: Decimal
    completed_workdays: int
    overtime_days: int
    overtime_seconds: int


@dataclass(frozen=True)
class OvertimeRecord:
    record_date: date
    overtime_seconds: int
    source: RecordSource

    def to_dict(self) -> dict:
        return {
            "date": self.record_date.isoformat(),
            "overtime_seconds": self.overtime_seconds,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OvertimeRecord":
        return cls(
            record_date=date.fromisoformat(str(data["date"])),
            overtime_seconds=max(0, int(data.get("overtime_seconds", 0))),
            source=str(data.get("source", "manual")),
        )
