from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class HistoryEntry:
    ts: int
    session_type: str
    duration: int
    task_id: str | None
    subject: str | None


def _parse(raw: list[dict]) -> list[HistoryEntry]:
    out = []
    for r in raw:
        try:
            out.append(HistoryEntry(
                ts=int(r["ts"]),
                session_type=r.get("session_type", "focus"),
                duration=r.get("duration", 0),
                task_id=r.get("task_id"),
                subject=r.get("subject"),
            ))
        except (KeyError, TypeError):
            continue
    return out


def today_entries(raw: list[dict]) -> list[HistoryEntry]:
    now = datetime.now(timezone.utc)
    today_date = now.date()
    return [
        e for e in _parse(raw)
        if datetime.fromtimestamp(e.ts, tz=timezone.utc).date() == today_date
    ]


def entries_in_range(raw: list[dict], start_ts: int, end_ts: int) -> list[HistoryEntry]:
    return [e for e in _parse(raw) if start_ts <= e.ts < end_ts]


def total_focus_seconds(entries: list[HistoryEntry]) -> int:
    return sum(e.duration for e in entries if e.session_type == "focus")


def per_task_seconds(entries: list[HistoryEntry]) -> dict[str, int]:
    result: dict[str, int] = {}
    for e in entries:
        if e.task_id is None or e.session_type != "focus":
            continue
        result[e.task_id] = result.get(e.task_id, 0) + e.duration
    return result


def per_subject_seconds(entries: list[HistoryEntry]) -> dict[str, int]:
    result: dict[str, int] = {}
    for e in entries:
        if e.subject is None or e.session_type != "focus":
            continue
        result[e.subject] = result.get(e.subject, 0) + e.duration
    return result


def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    if minutes >= 60:
        h, m = divmod(minutes, 60)
        return f"{h}h {m}m"
    return f"{minutes}m"
