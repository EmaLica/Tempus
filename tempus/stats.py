from datetime import datetime, timezone, timedelta
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from . import history as hist
from . import storage

_RANGES = [
    ("today", "Today"),
    ("week", "Week"),
    ("month", "Month"),
    ("semester", "Semester"),
]


class StatsPanel(Gtk.Box):
    __gtype_name__ = "TempusStatsPanel"

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._range = "today"
        self._settings: Gio.Settings | None = None
        try:
            self._settings = Gio.Settings.new("io.github.EmaLica.Tempus")
        except Exception:
            pass
        self._build_ui()

    def _build_ui(self) -> None:
        pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        pill.add_css_class("linked")
        pill.set_halign(Gtk.Align.CENTER)
        pill.set_margin_top(12)
        pill.set_margin_bottom(12)
        pill.set_margin_start(12)
        pill.set_margin_end(12)

        self._range_btns: dict[str, Gtk.ToggleButton] = {}
        first = None
        for key, label in _RANGES:
            btn = Gtk.ToggleButton(label=label)
            if first is None:
                first = btn
            else:
                btn.set_group(first)
            btn.connect("toggled", self._on_range_toggled, key)
            pill.append(btn)
            self._range_btns[key] = btn

        self.append(pill)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._scroll = scroll
        scroll.set_child(self._inner)
        self.append(scroll)

    def _on_range_toggled(self, btn: Gtk.ToggleButton, key: str) -> None:
        if btn.get_active():
            self._range = key
            self._render()

    def refresh(self) -> None:
        self._range_btns["today"].set_active(True)
        if self._range == "today":
            self._render()

    def _range_timestamps(self) -> tuple[int, int]:
        now = datetime.now(timezone.utc)
        end = int(now.timestamp()) + 1

        if self._range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return int(start.timestamp()), end

        if self._range == "week":
            start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            return int(start.timestamp()), end

        if self._range == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return int(start.timestamp()), end

        if self._settings:
            try:
                if self._settings.get_boolean("semester-custom"):
                    s = self._settings.get_string("semester-start")
                    e = self._settings.get_string("semester-end")
                    if s and e:
                        s_dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
                        e_dt = datetime.fromisoformat(e).replace(tzinfo=timezone.utc)
                        return int(s_dt.timestamp()), int(e_dt.timestamp()) + 86400
            except Exception:
                pass

        start = now - timedelta(days=183)
        return int(start.timestamp()), end

    def _clear_inner(self) -> None:
        child = self._inner.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._inner.remove(child)
            child = nxt
        adj = self._scroll.get_vadjustment()
        if adj:
            adj.set_value(0.0)

    def _render(self) -> None:
        self._clear_inner()

        start_ts, end_ts = self._range_timestamps()
        raw = storage.load_history()
        entries = hist.entries_in_range(raw, start_ts, end_ts)
        focus = [e for e in entries if e.session_type == "focus"]
        total_secs = hist.total_focus_seconds(focus)

        if not focus or total_secs == 0:
            status = Adw.StatusPage()
            status.set_icon_name("preferences-system-time-symbolic")
            status.set_title("No sessions yet")
            status.set_description("Start a focus session to see your stats here.")
            status.set_vexpand(True)
            self._inner.append(status)
            return

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero.set_margin_top(24)
        hero.set_margin_bottom(16)
        hero.set_halign(Gtk.Align.CENTER)

        total_lbl = Gtk.Label(label=hist.format_duration(total_secs))
        total_lbl.add_css_class("title-1")
        hero.append(total_lbl)

        n = len(focus)
        sub = Gtk.Label(label=f"{n} focus session{'s' if n != 1 else ''}")
        sub.add_css_class("dim-label")
        sub.add_css_class("caption-heading")
        hero.append(sub)

        self._inner.append(hero)
        self._inner.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        if self._range == "today":
            self._render_by_task(focus)
        else:
            self._render_by_subject(focus)

    def _render_by_task(self, focus: list) -> None:
        by_task = hist.per_task_seconds(focus)
        if not by_task:
            lbl = Gtk.Label(label="No task was active during today's sessions.")
            lbl.add_css_class("dim-label")
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_margin_top(24)
            lbl.set_margin_bottom(24)
            lbl.set_wrap(True)
            self._inner.append(lbl)
            return

        raw_tasks = storage.load_tasks()
        task_map = {r["id"]: r["text"] for r in raw_tasks if "id" in r}
        max_secs = max(by_task.values())

        group = Adw.PreferencesGroup()
        group.set_title("By task")
        group.set_margin_top(16)
        group.set_margin_bottom(16)
        group.set_margin_start(12)
        group.set_margin_end(12)

        for task_id, secs in sorted(by_task.items(), key=lambda x: -x[1]):
            n = sum(1 for e in focus if e.task_id == task_id)
            row = Adw.ActionRow()
            row.set_title(GLib.markup_escape_text(task_map.get(task_id, "Deleted task")))
            row.set_subtitle(f"{n} session{'s' if n != 1 else ''} · {hist.format_duration(secs)}")
            row.add_suffix(self._level_bar(secs, max_secs))
            group.add(row)

        self._inner.append(group)

    def _render_by_subject(self, focus: list) -> None:
        by_subject = hist.per_subject_seconds(focus)
        if not by_subject:
            lbl = Gtk.Label(label="No subject was assigned during these sessions.")
            lbl.add_css_class("dim-label")
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_margin_top(24)
            lbl.set_margin_bottom(24)
            lbl.set_wrap(True)
            self._inner.append(lbl)
            return

        max_secs = max(by_subject.values())

        group = Adw.PreferencesGroup()
        group.set_title("By subject")
        group.set_margin_top(16)
        group.set_margin_bottom(16)
        group.set_margin_start(12)
        group.set_margin_end(12)

        for subject, secs in sorted(by_subject.items(), key=lambda x: -x[1]):
            n = sum(1 for e in focus if e.subject == subject)
            row = Adw.ActionRow()
            row.set_title(GLib.markup_escape_text(subject))
            row.set_subtitle(f"{n} session{'s' if n != 1 else ''} · {hist.format_duration(secs)}")
            row.add_suffix(self._level_bar(secs, max_secs))
            group.add(row)

        self._inner.append(group)

    def _level_bar(self, value: int, maximum: int) -> Gtk.LevelBar:
        bar = Gtk.LevelBar()
        bar.set_mode(Gtk.LevelBarMode.CONTINUOUS)
        bar.set_min_value(0.0)
        bar.set_max_value(1.0)
        bar.set_value(value / maximum)
        bar.set_size_request(120, -1)
        bar.set_valign(Gtk.Align.CENTER)
        return bar
