import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from salary_tick.calendar_service import month_workdays
from salary_tick.settings_store import CONFIG_VERSION, SettingsStore


class FakeDate(date):
    current = date(2026, 12, 1)

    @classmethod
    def today(cls):
        return cls.current


class SettingsBoundaryTests(unittest.TestCase):
    def base_config(self):
        return {
            "config_version": CONFIG_VERSION,
            "setup_completed": True,
            "profile": {
                "year": 2026,
                "month": 11,
                "monthly_salary": "10000",
                "workdays": "20",
                "manual_workdays": True,
                "overtime_multiplier": "1.5",
                "work_start": "08:15",
                "lunch_start": "11:45",
                "lunch_end": "12:45",
                "work_end": "17:15",
                "overtime_start": "17:45",
            },
            "today": {"date": "2026-11-30", "expected_end": "19:15"},
            "display": {
                "refresh_mode": "秒表",
                "privacy_mode": "手动切换",
                "float_amount_visible": False,
            },
            "window": {"float_open": True, "float_x": 30, "float_y": 30},
            "behavior": {
                "skip_close_confirmation": False,
                "reset_expected_end_daily": True,
            },
        }

    def load_on(self, config, current_date):
        FakeDate.current = current_date
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
            with patch("salary_tick.settings_store.date", FakeDate):
                return SettingsStore(path).load()

    def test_cross_month_updates_year_and_month(self):
        loaded = self.load_on(self.base_config(), date(2026, 12, 1))
        self.assertEqual((loaded["profile"]["year"], loaded["profile"]["month"]), (2026, 12))

    def test_cross_month_recalculates_workdays(self):
        loaded = self.load_on(self.base_config(), date(2026, 12, 1))
        self.assertEqual(loaded["profile"]["workdays"], str(month_workdays(2026, 12)))

    def test_cross_month_clears_manual_workday_override(self):
        loaded = self.load_on(self.base_config(), date(2026, 12, 1))
        self.assertFalse(loaded["profile"]["manual_workdays"])

    def test_cross_month_resets_expected_end_even_when_daily_reset_disabled(self):
        config = self.base_config()
        config["behavior"]["reset_expected_end_daily"] = False
        loaded = self.load_on(config, date(2026, 12, 1))
        self.assertEqual(loaded["today"]["expected_end"], "17:15")

    def test_same_month_new_day_resets_expected_end_when_enabled(self):
        config = self.base_config()
        config["profile"]["month"] = 11
        config["today"] = {"date": "2026-11-17", "expected_end": "19:15"}
        loaded = self.load_on(config, date(2026, 11, 18))
        self.assertEqual(loaded["today"]["expected_end"], "17:15")

    def test_same_month_new_day_preserves_expected_end_when_disabled(self):
        config = self.base_config()
        config["profile"]["month"] = 11
        config["behavior"]["reset_expected_end_daily"] = False
        config["today"] = {"date": "2026-11-17", "expected_end": "19:15"}
        loaded = self.load_on(config, date(2026, 11, 18))
        self.assertEqual(loaded["today"]["expected_end"], "19:15")

    def test_same_day_does_not_change_expected_end(self):
        config = self.base_config()
        config["profile"]["month"] = 11
        config["today"] = {"date": "2026-11-18", "expected_end": "19:15"}
        loaded = self.load_on(config, date(2026, 11, 18))
        self.assertEqual(loaded["today"]["expected_end"], "19:15")

    def test_cross_year_updates_to_january(self):
        config = self.base_config()
        config["profile"]["year"] = 2026
        config["profile"]["month"] = 12
        config["today"] = {"date": "2026-12-31", "expected_end": "18:15"}
        loaded = self.load_on(config, date(2027, 1, 1))
        self.assertEqual((loaded["profile"]["year"], loaded["profile"]["month"]), (2027, 1))


if __name__ == "__main__":
    unittest.main()
