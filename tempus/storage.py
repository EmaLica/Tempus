import json
from pathlib import Path

DATA_DIR = Path.home() / ".local" / "share" / "tempus"


def load_tasks() -> list[dict]:
    path = DATA_DIR / "tasks.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_tasks(tasks: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_DIR / "tasks.json.tmp"
    tmp.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DATA_DIR / "tasks.json")


def load_history() -> list[dict]:
    path = DATA_DIR / "history.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_history(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.append(entry)
    tmp = DATA_DIR / "history.json.tmp"
    tmp.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DATA_DIR / "history.json")
