import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from . import history as hist
from . import storage


class StatsPanel(Gtk.Box):
    __gtype_name__ = "TempusStatsPanel"

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._scroll = scroll
        scroll.set_child(self._inner)
        self.append(scroll)

    def refresh(self) -> None:
        child = self._inner.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._inner.remove(child)
            child = nxt

        adj = self._scroll.get_vadjustment()
        if adj:
            adj.set_value(0.0)

        raw_history = storage.load_history()
        raw_tasks = storage.load_tasks()
        today = hist.today_entries(raw_history)
        total_secs = hist.total_focus_seconds(today)
        by_task = hist.per_task_seconds(today)

        if not today or total_secs == 0:
            status = Adw.StatusPage()
            status.set_icon_name("preferences-system-time-symbolic")
            status.set_title("No sessions yet today")
            status.set_description("Start a focus session to see your stats here.")
            status.set_vexpand(True)
            self._inner.append(status)
            return

        # hero row — big total at the top
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero.set_margin_top(24)
        hero.set_margin_bottom(16)
        hero.set_margin_start(24)
        hero.set_margin_end(24)
        hero.set_halign(Gtk.Align.CENTER)

        total_label = Gtk.Label(label=hist.format_duration(total_secs))
        total_label.add_css_class("title-1")
        hero.append(total_label)

        session_count = len([e for e in today if e.session_type == "focus"])
        sub_text = f"{session_count} focus session{'s' if session_count != 1 else ''} today"
        sub = Gtk.Label(label=sub_text)
        sub.add_css_class("dim-label")
        sub.add_css_class("caption-heading")
        hero.append(sub)

        self._inner.append(hero)
        self._inner.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        if not by_task:
            lbl = Gtk.Label(label="No task was active during today's sessions.")
            lbl.add_css_class("dim-label")
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_margin_top(24)
            lbl.set_margin_bottom(24)
            lbl.set_margin_start(12)
            lbl.set_margin_end(12)
            lbl.set_wrap(True)
            self._inner.append(lbl)
            return

        task_map = {r["id"]: r["text"] for r in raw_tasks if "id" in r}
        max_secs = max(by_task.values())

        group = Adw.PreferencesGroup()
        group.set_title("By task")
        group.set_margin_top(16)
        group.set_margin_bottom(16)
        group.set_margin_start(12)
        group.set_margin_end(12)

        for task_id, secs in sorted(by_task.items(), key=lambda x: -x[1]):
            task_text = task_map.get(task_id, "Deleted task")
            n_sessions = sum(
                1 for e in today
                if e.task_id == task_id and e.session_type == "focus"
            )

            row = Adw.ActionRow()
            row.set_title(GLib.markup_escape_text(task_text))
            row.set_subtitle(
                f"{n_sessions} session{'s' if n_sessions != 1 else ''} · {hist.format_duration(secs)}"
            )

            bar = Gtk.LevelBar()
            bar.set_mode(Gtk.LevelBarMode.CONTINUOUS)
            bar.set_min_value(0.0)
            bar.set_max_value(1.0)
            bar.set_value(secs / max_secs)
            bar.set_size_request(120, -1)
            bar.set_valign(Gtk.Align.CENTER)
            row.add_suffix(bar)

            group.add(row)

        self._inner.append(group)
