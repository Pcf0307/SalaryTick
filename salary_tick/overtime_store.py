from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from .models import OvertimeRecord
from .settings_store import local_app_data_dir


def app_data_dir() -> Path:
    return local_app_data_dir()



class OvertimeStore:
    def __init__(self, path: Path | None = None):
        self.path = path or app_data_dir() / "overtime_records.json"

    def load(self) -> dict[str, OvertimeRecord]:
        try:
            if not self.path.exists():
                return {}
            data = json.loads(self.path.read_text(encoding="utf-8"))
            result: dict[str, OvertimeRecord] = {}
            for key, item in data.get("records", {}).items():
                payload = dict(item)
                payload.setdefault("date", key)
                record = OvertimeRecord.from_dict(payload)
                result[record.record_date.isoformat()] = record
            return result
        except (OSError, ValueError, TypeError, KeyError):
            return {}

    def save(self, records: dict[str, OvertimeRecord]) -> None:
        payload = {
            "records": {
                key: {
                    "overtime_seconds": record.overtime_seconds,
                    "source": record.source,
                }
                for key, record in records.items()
            }
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def upsert(self, record: OvertimeRecord, records: dict[str, OvertimeRecord]) -> None:
        records[record.record_date.isoformat()] = record
        self.save(records)

    def delete(self, record_date: date, records: dict[str, OvertimeRecord]) -> None:
        records.pop(record_date.isoformat(), None)
        self.save(records)
