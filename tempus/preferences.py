import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

from .timer import SessionType


SETTINGS_KEYS = {
    SessionType.FOCUS: ("focus-duration", 25),
    SessionType.SHORT_BREAK: ("short-break-duration", 5),
    SessionType.LONG_BREAK: ("long-break-duration", 15),
    SessionType.CUSTOM: ("custom-duration", 10),
}


class TempusPreferences(Adw.PreferencesWindow):
    def __init__(self, timer=None, **kwargs):
        super().__init__(**kwargs)
        self.timer = timer
        self.set_title("Preferences")
        self.set_default_size(480, 420)
        self.set_search_enabled(False)

        try:
            self._settings = Gio.Settings.new("io.github.EmaLica.Tempus")
        except Exception:
            self._settings = None

        self._build_ui()

    def _build_ui(self):
        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("preferences-system-symbolic")

        # ── Duration group ──────────────────────────────────────────────────
        dur_group = Adw.PreferencesGroup()
        dur_group.set_title("Session Durations")
        dur_group.set_description("Duration in minutes for each session type")

        self._spin_rows: dict[SessionType, Adw.SpinRow] = {}
        labels = {
            SessionType.FOCUS: "Focus",
            SessionType.SHORT_BREAK: "Short Break",
            SessionType.LONG_BREAK: "Long Break",
            SessionType.CUSTOM: "Custom",
        }
        ranges = {
            SessionType.FOCUS: (1, 90),
            SessionType.SHORT_BREAK: (1, 30),
            SessionType.LONG_BREAK: (1, 60),
            SessionType.CUSTOM: (1, 120),
        }
        for stype, label in labels.items():
            key, default = SETTINGS_KEYS[stype]
            lo, hi = ranges[stype]
            row = self._make_spin(label, key, lo, hi, default)
            self._spin_rows[stype] = row
            dur_group.add(row)

        page.add(dur_group)

        # ── Cycle group ─────────────────────────────────────────────────────
        cycle_group = Adw.PreferencesGroup()
        cycle_group.set_title("Pomodoro Cycle")

        self._cycle_row = self._make_spin(
            "Focus sessions before long break",
            "sessions-before-long-break",
            1, 10, 4,
        )
        cycle_group.add(self._cycle_row)
        page.add(cycle_group)

        # ── GNOME integration group ─────────────────────────────────────────
        gnome_group = Adw.PreferencesGroup()
        gnome_group.set_title("GNOME Integration")

        dnd_row = Adw.SwitchRow()
        dnd_row.set_title("Focus mode")
        dnd_row.set_subtitle("Disable notifications while a focus session is running")

        if self._settings:
            try:
                dnd_row.set_active(self._settings.get_boolean("dnd-during-focus"))
            except Exception:
                dnd_row.set_active(True)

        dnd_row.connect("notify::active", self._on_dnd_changed)
        gnome_group.add(dnd_row)
        page.add(gnome_group)

        self.add(page)

    def _make_spin(self, title: str, key: str, lo: int, hi: int, default: int) -> Adw.SpinRow:
        row = Adw.SpinRow()
        row.set_title(title)

        value = default
        if self._settings:
            try:
                value = self._settings.get_int(key)
            except Exception:
                pass
        adj = Gtk.Adjustment(value=value, lower=lo, upper=hi, step_increment=1, page_increment=5)
        row.set_adjustment(adj)
        row.connect("notify::value", self._on_value_changed, key)
        return row

    def _on_value_changed(self, row: Adw.SpinRow, _param, key: str):
        value = int(row.get_value())
        if self._settings:
            self._settings.set_int(key, value)
        if self.timer:
            self._apply_to_timer(key, value)

    def _on_dnd_changed(self, row: Adw.SwitchRow, _param) -> None:
        if self._settings:
            try:
                self._settings.set_boolean("dnd-during-focus", row.get_active())
            except Exception:
                pass

    def _apply_to_timer(self, key: str, value: int):
        mapping = {v[0]: k for k, v in SETTINGS_KEYS.items()}
        if key in mapping:
            stype = mapping[key]
            self.timer.durations[stype] = value * 60
            if stype == self.timer.session_type:
                self.timer.reload_durations()
        elif key == "sessions-before-long-break":
            self.timer.sessions_before_long_break = value
