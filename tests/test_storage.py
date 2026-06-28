import json
import pytest
from pathlib import Path


def test_load_tasks_returns_empty_list_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    from tempus import storage
    result = storage.load_tasks()
    assert result == []


def test_save_and_load_tasks_roundtrip(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    tasks = [
        {"id": "abc", "text": "Write report", "done": False, "pomodoros": 2, "estimate": 0}
    ]
    storage.save_tasks(tasks)
    loaded = storage.load_tasks()
    assert loaded == tasks


def test_load_tasks_handles_corrupt_file(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    (tmp_path / "tasks.json").write_text("not valid json")
    result = storage.load_tasks()
    assert result == []


def test_load_history_returns_empty_when_missing(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    result = storage.load_history()
    assert result == []


def test_append_history_creates_file_and_accumulates(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    entry1 = {"ts": 1000, "session_type": "focus", "duration": 1500, "task_id": "abc"}
    entry2 = {"ts": 2000, "session_type": "focus", "duration": 1500, "task_id": None}
    storage.append_history(entry1)
    storage.append_history(entry2)
    result = storage.load_history()
    assert result == [entry1, entry2]


def test_append_history_handles_corrupt_existing_file(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    (tmp_path / "history.json").write_text("not valid json")
    entry = {"ts": 1000, "session_type": "focus", "duration": 1500, "task_id": None}
    storage.append_history(entry)
    result = storage.load_history()
    assert result == [entry]


def test_load_subjects_migrates_plain_strings(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    (tmp_path / "subjects.json").write_text(json.dumps(["Math", "Physics"]))
    result = storage.load_subjects()
    assert [s["name"] for s in result] == ["Math", "Physics"]
    assert all(s["color"].startswith("#") for s in result)
    assert result[0]["color"] != result[1]["color"]


def test_save_and_load_subjects_roundtrip(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    subjects = [{"name": "Logic", "color": "#3584e4"}]
    storage.save_subjects(subjects)
    assert storage.load_subjects() == subjects


def test_subject_color_lookup(tmp_path, monkeypatch):
    from tempus import storage
    monkeypatch.setattr("tempus.storage.DATA_DIR", tmp_path)
    storage.save_subjects([{"name": "Logic", "color": "#9141ac"}])
    assert storage.subject_color("Logic") == "#9141ac"
    assert storage.subject_color("Unknown") is None
