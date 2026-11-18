import tempfile
import unittest
from datetime import date
from pathlib import Path

from salary_tick.models import OvertimeRecord
from salary_tick.overtime_store import OvertimeStore
from salary_tick.settings_store import SettingsStore


class StoreTests(unittest.TestCase):
    def test_overtime_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store = OvertimeStore(Path(folder) / "overtime.json")
            records = {}
            store.upsert(OvertimeRecord(date(2026, 11, 2), 5400, "manual"), records)
            loaded = store.load()
            self.assertEqual(loaded["2026-11-02"].overtime_seconds, 5400)
            self.assertEqual(loaded["2026-11-02"].source, "manual")

    def test_corrupt_settings_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("not-json", encoding="utf-8")
            loaded = SettingsStore(path).load()
            self.assertEqual(loaded["profile"]["monthly_salary"], "10000")
            self.assertIn("expected_end", loaded["today"])
            self.assertEqual(loaded["config_version"], 2)

    def test_overtime_save_is_atomic_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "overtime_records.json"
            store = OvertimeStore(path)
            records = {"2026-11-02": OvertimeRecord(date(2026, 11, 2), 5400, "manual")}
            store.save(records)
            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix(".tmp").exists())
            self.assertEqual(store.load()["2026-11-02"].overtime_seconds, 5400)


if __name__ == "__main__":
    unittest.main()
