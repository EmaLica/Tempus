import json
import pytest
from pathlib import Path


def test_load_tasks_returns_empty_list_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    from tempus import storage
    storage.DATA_DIR = tmp_path
    result = storage.load_tasks()
    assert result == []


def test_save_and_load_tasks_roundtrip(tmp_path):
    from tempus import storage
    storage.DATA_DIR = tmp_path
    tasks = [
        {"id": "abc", "text": "Write report", "done": False, "pomodoros": 2, "estimate": 0}
    ]
    storage.save_tasks(tasks)
    loaded = storage.load_tasks()
    assert loaded == tasks


def test_load_tasks_handles_corrupt_file(tmp_path):
    from tempus import storage
    storage.DATA_DIR = tmp_path
    (tmp_path / "tasks.json").write_text("not valid json")
    result = storage.load_tasks()
    assert result == []


def test_load_history_returns_empty_when_missing(tmp_path):
    from tempus import storage
    storage.DATA_DIR = tmp_path
    result = storage.load_history()
    assert result == []


def test_append_history_creates_file_and_accumulates(tmp_path):
    from tempus import storage
    storage.DATA_DIR = tmp_path
    entry1 = {"ts": 1000, "session_type": "focus", "duration": 1500, "task_id": "abc"}
    entry2 = {"ts": 2000, "session_type": "focus", "duration": 1500, "task_id": None}
    storage.append_history(entry1)
    storage.append_history(entry2)
    result = storage.load_history()
    assert result == [entry1, entry2]


def test_append_history_handles_corrupt_existing_file(tmp_path):
    from tempus import storage
    storage.DATA_DIR = tmp_path
    (tmp_path / "history.json").write_text("not valid json")
    entry = {"ts": 1000, "session_type": "focus", "duration": 1500, "task_id": None}
    storage.append_history(entry)
    result = storage.load_history()
    assert result == [entry]
