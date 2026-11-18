from __future__ import annotations

from datetime import datetime


def parse_hhmm(value: str):
    return datetime.strptime(value.strip(), "%H:%M").time()


def normalize_amount_visibility(privacy_mode: str, requested: bool) -> bool:
    """Only direct-display mode may restore a saved visible amount state."""
    return bool(requested) if privacy_mode == "直接显示" else False


def normalize_expected_end(work_end: str, expected_end: str) -> str:
    """Expected end may not precede the configured normal work end."""
    return work_end if parse_hhmm(expected_end) < parse_hhmm(work_end) else expected_end
