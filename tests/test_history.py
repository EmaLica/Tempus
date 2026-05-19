import time
import pytest
from datetime import datetime, timezone


def _make_entry(ts: int, task_id=None, duration=1500) -> dict:
    return {"ts": ts, "session_type": "focus", "duration": duration, "task_id": task_id}


def _today_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp())


def test_today_entries_filters_to_today():
    from tempus import history
    today = _today_ts()
    entries = [
        _make_entry(today + 100, task_id="a"),
        _make_entry(today - 90000, task_id="b"),  # yesterday
        _make_entry(today + 3600, task_id="c"),
    ]
    result = history.today_entries(entries)
    assert len(result) == 2
    assert all(e.task_id != "b" for e in result)


def test_today_entries_empty_input():
    from tempus import history
    assert history.today_entries([]) == []


def test_total_focus_seconds_sums_durations():
    from tempus import history
    today = _today_ts()
    entries = [
        _make_entry(today + 10, duration=1500),
        _make_entry(today + 20, duration=900),
    ]
    result = history.total_focus_seconds(history.today_entries(entries))
    assert result == 2400


def test_per_task_seconds_groups_by_task():
    from tempus import history
    today = _today_ts()
    entries = [
        _make_entry(today + 10, task_id="x", duration=1500),
        _make_entry(today + 20, task_id="x", duration=1500),
        _make_entry(today + 30, task_id="y", duration=900),
        _make_entry(today + 40, task_id=None, duration=600),
    ]
    result = history.per_task_seconds(history.today_entries(entries))
    assert result["x"] == 3000
    assert result["y"] == 900
    assert None not in result


def test_format_duration_hours_and_minutes():
    from tempus import history
    assert history.format_duration(3600) == "1h 0m"
    assert history.format_duration(2700) == "45m"
    assert history.format_duration(90) == "1m"
    assert history.format_duration(0) == "0m"
