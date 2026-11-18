from __future__ import annotations

import json
import os
import shutil
from datetime import date
from pathlib import Path

CONFIG_VERSION = 2

DEFAULT_CONFIG = {
    "config_version": CONFIG_VERSION,
    "setup_completed": False,
    "profile": {
        "year": date.today().year,
        "month": date.today().month,
        "monthly_salary": "10000",
        "workdays": "21",
        "manual_workdays": False,
        "overtime_multiplier": "1.5",
        "work_start": "08:15",
        "lunch_start": "11:45",
        "lunch_end": "12:45",
        "work_end": "17:15",
        "overtime_start": "17:45",
    },
    "today": {"date": date.today().isoformat(), "expected_end": "17:15"},
    "display": {"refresh_mode": "秒表", "privacy_mode": "手动切换", "float_amount_visible": False, "language": "zh_CN"},
    "window": {"float_open": False, "float_x": 30, "float_y": 30},
    "behavior": {"skip_close_confirmation": False, "reset_expected_end_daily": True},
}


def local_app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    folder = Path(base) / "SalaryTick" if base else Path.home() / ".salary_tick"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def roaming_app_data_dir() -> Path | None:
    base = os.environ.get("APPDATA")
    return Path(base) / "SalaryTick" if base else None


def _deep_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def _deep_merge(base: dict, incoming: dict) -> dict:
    result = _deep_copy(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or local_app_data_dir() / "settings.json"
        if path is None:
            self._migrate_roaming_files()

    def _migrate_roaming_files(self) -> None:
        old_dir = roaming_app_data_dir()
        if not old_dir or old_dir.resolve() == self.path.parent.resolve():
            return
        for name in ("settings.json", "overtime_records.json", "ui_preferences.json"):
            source, target = old_dir / name, self.path.parent / name
            if source.exists() and not target.exists():
                try:
                    shutil.copy2(source, target)
                except OSError:
                    pass

    def load(self) -> dict:
        raw = {}
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                raw = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError, TypeError):
            raw = {}
        is_v2 = raw.get("config_version") == CONFIG_VERSION and "profile" in raw
        config = self._normalize(raw)
        if not is_v2:
            self._merge_legacy_ui_preference(config)
        self._apply_calendar_boundary(config)
        if not is_v2 and raw:
            self.save(config)
        return config

    def _normalize(self, raw: dict) -> dict:
        if raw.get("config_version") == CONFIG_VERSION and "profile" in raw:
            return _deep_merge(DEFAULT_CONFIG, raw)
        if not raw:
            return _deep_copy(DEFAULT_CONFIG)
        # Version 1 flat settings migration.
        config = _deep_copy(DEFAULT_CONFIG)
        profile = config["profile"]
        for key in profile:
            if key in raw:
                profile[key] = raw[key]
        config["today"]["date"] = raw.get("expected_end_date", date.today().isoformat())
        config["today"]["expected_end"] = raw.get("expected_end", profile["work_end"])
        config["display"]["refresh_mode"] = raw.get("refresh_mode", "秒表")
        config["display"]["privacy_mode"] = raw.get("privacy_mode", "手动切换")
        config["display"]["float_amount_visible"] = bool(raw.get("float_amount_visible", False))
        for key in ("float_open", "float_x", "float_y"):
            if key in raw:
                config["window"][key] = raw[key]
        config["setup_completed"] = bool(raw.get("setup_completed", True))
        return config

    def _merge_legacy_ui_preference(self, config: dict) -> None:
        legacy = self.path.parent / "ui_preferences.json"
        try:
            if legacy.exists():
                value = json.loads(legacy.read_text(encoding="utf-8"))
                config["behavior"]["skip_close_confirmation"] = bool(value.get("skip_close_confirmation", False))
        except (OSError, ValueError, TypeError):
            pass

    @staticmethod
    def _apply_calendar_boundary(config: dict) -> None:
        today = date.today()
        today_text = today.isoformat()
        profile = config["profile"]
        behavior = config["behavior"]
        saved_year = int(profile.get("year", today.year))
        saved_month = int(profile.get("month", today.month))
        month_changed = (saved_year, saved_month) != (today.year, today.month)

        if month_changed:
            # 工作日手动覆盖只属于原工资月份，不跨月继承。
            from .calendar_service import month_workdays
            profile["year"] = today.year
            profile["month"] = today.month
            profile["manual_workdays"] = False
            profile["workdays"] = str(month_workdays(today.year, today.month))

        if config["today"].get("date") != today_text:
            expected_end = (
                profile["work_end"]
                if behavior.get("reset_expected_end_daily", True) or month_changed
                else config["today"].get("expected_end", profile["work_end"])
            )
            config["today"] = {"date": today_text, "expected_end": expected_end}

    def save(self, config: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def open_directory(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path.parent
