import json
from pathlib import Path
import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from . import palette

DATA_DIR = Path(GLib.get_user_data_dir()) / "tempus"

# dentro il sandbox le impostazioni di org.gnome.desktop.* finiscono nel dconf
# privato dell'app e non toccano l'host, quindi il focus mode va disattivato
IN_SANDBOX = Path("/.flatpak-info").exists()


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


def load_subjects() -> list[dict]:
    try:
        raw = json.loads((DATA_DIR / "subjects.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for i, s in enumerate(raw):
        if isinstance(s, str):
            out.append({"name": s, "color": palette.default_color(i)})
        elif isinstance(s, dict) and s.get("name"):
            out.append({"name": s["name"], "color": s.get("color") or palette.default_color(i)})
    return out


def save_subjects(subjects: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_DIR / "subjects.json.tmp"
    tmp.write_text(json.dumps(subjects, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DATA_DIR / "subjects.json")


def subject_color(name: str) -> str | None:
    for s in load_subjects():
        if s["name"] == name:
            return s["color"]
    return None


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
