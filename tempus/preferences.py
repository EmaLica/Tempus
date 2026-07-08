import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

from .timer import SessionType
from . import storage
from . import palette


def _swatch_css(widget: Gtk.Widget, color: str) -> None:
    prov = Gtk.CssProvider()
    css = f"* {{ background:{color}; border-radius:5px; min-width:18px; min-height:18px; }}"
    try:
        prov.load_from_string(css)
    except AttributeError:
        prov.load_from_data(css.encode())
    widget.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


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
        self.set_default_size(480, 560)
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

        cycle_group = Adw.PreferencesGroup()
        cycle_group.set_title("Pomodoro Cycle")
        self._cycle_row = self._make_spin(
            "Focus sessions before long break",
            "sessions-before-long-break",
            1, 10, 4,
        )
        cycle_group.add(self._cycle_row)
        page.add(cycle_group)

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

        notif_group = Adw.PreferencesGroup()
        notif_group.set_title("Notifications")

        vol_row = Adw.ActionRow()
        vol_row.set_title("Alert volume")

        vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        vol_scale.set_hexpand(True)
        vol_scale.set_draw_value(True)
        vol_scale.set_value_pos(Gtk.PositionType.RIGHT)
        vol_scale.set_size_request(180, -1)

        vol_default = 70
        if self._settings:
            try:
                vol_default = self._settings.get_int("alert-volume")
            except Exception:
                pass
        vol_scale.set_value(vol_default)
        vol_scale.connect("value-changed", self._on_volume_changed)
        vol_row.add_suffix(vol_scale)
        vol_row.set_activatable_widget(vol_scale)
        notif_group.add(vol_row)

        start_row = Adw.SwitchRow()
        start_row.set_title("Session start sound")
        start_row.set_subtitle("Play a sound when you start a session")
        if self._settings:
            try:
                start_row.set_active(self._settings.get_boolean("start-sound"))
            except Exception:
                start_row.set_active(True)
        start_row.connect("notify::active", self._on_start_sound_changed)
        notif_group.add(start_row)
        page.add(notif_group)

        self._subjects_group = Adw.PreferencesGroup()
        self._subjects_group.set_title("Subjects")
        self._subjects_group.set_description("Subjects you can assign to tasks")
        self._subject_rows: list[tuple[str, Adw.ActionRow]] = []

        self._new_subject_row = Adw.EntryRow()
        self._new_subject_row.set_title("Add subject…")
        self._new_subject_row.set_show_apply_button(True)
        self._new_subject_row.connect("apply", self._on_add_subject)
        self._subjects_group.add(self._new_subject_row)

        self._rebuild_subject_rows()
        page.add(self._subjects_group)

        semester_group = Adw.PreferencesGroup()
        semester_group.set_title("Semester")

        self._semester_switch = Adw.SwitchRow()
        self._semester_switch.set_title("Custom date range")
        self._semester_switch.set_subtitle("Off uses the last 6 months")

        self._semester_start = Adw.EntryRow()
        self._semester_start.set_title("Start date (YYYY-MM-DD)")

        self._semester_end = Adw.EntryRow()
        self._semester_end.set_title("End date (YYYY-MM-DD)")

        if self._settings:
            try:
                custom = self._settings.get_boolean("semester-custom")
                self._semester_switch.set_active(custom)
                self._semester_start.set_text(self._settings.get_string("semester-start"))
                self._semester_end.set_text(self._settings.get_string("semester-end"))
            except Exception:
                pass

        self._semester_start.set_visible(self._semester_switch.get_active())
        self._semester_end.set_visible(self._semester_switch.get_active())

        self._semester_switch.connect("notify::active", self._on_semester_switch_changed)
        self._semester_start.connect("changed", self._on_semester_date_changed, "semester-start")
        self._semester_end.connect("changed", self._on_semester_date_changed, "semester-end")

        semester_group.add(self._semester_switch)
        semester_group.add(self._semester_start)
        semester_group.add(self._semester_end)
        page.add(semester_group)

        self.add(page)

    def _rebuild_subject_rows(self):
        for _, row in self._subject_rows:
            self._subjects_group.remove(row)
        self._subject_rows.clear()

        for entry in storage.load_subjects():
            name = entry["name"]
            row = Adw.ActionRow()
            row.set_title(name)

            swatch = self._make_swatch(entry["color"])
            swatch.connect("clicked", self._on_edit_color, name)
            row.add_prefix(swatch)

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", self._on_delete_subject, name)
            row.add_suffix(del_btn)

            self._subjects_group.add(row)
            self._subject_rows.append((name, row))

    def _make_swatch(self, color: str) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.set_valign(Gtk.Align.CENTER)
        sq = Gtk.Box()
        sq.set_size_request(18, 18)
        _swatch_css(sq, color)
        btn.set_child(sq)
        return btn

    def _on_edit_color(self, btn: Gtk.Button, name: str):
        pop = Gtk.Popover()
        pop.set_parent(btn)
        grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        for color in palette.SUBJECT_COLORS:
            sw = self._make_swatch(color)
            sw.connect("clicked", self._on_pick_color, name, color, pop)
            grid.append(sw)
        pop.set_child(grid)
        pop.popup()

    def _on_pick_color(self, _btn, name: str, color: str, pop: Gtk.Popover):
        subjects = storage.load_subjects()
        for s in subjects:
            if s["name"] == name:
                s["color"] = color
        storage.save_subjects(subjects)
        self._rebuild_subject_rows()
        pop.popdown()

    def _on_add_subject(self, row: Adw.EntryRow):
        text = row.get_text().strip()
        if not text:
            return
        subjects = storage.load_subjects()
        if not any(s["name"] == text for s in subjects):
            subjects.append({"name": text, "color": palette.default_color(len(subjects))})
            storage.save_subjects(subjects)
            self._rebuild_subject_rows()
        row.set_text("")

    def _on_delete_subject(self, _btn, name: str):
        subjects = [s for s in storage.load_subjects() if s["name"] != name]
        storage.save_subjects(subjects)
        self._rebuild_subject_rows()

    def _on_semester_switch_changed(self, row: Adw.SwitchRow, _param):
        active = row.get_active()
        self._semester_start.set_visible(active)
        self._semester_end.set_visible(active)
        if self._settings:
            try:
                self._settings.set_boolean("semester-custom", active)
            except Exception:
                pass

    def _on_semester_date_changed(self, row: Adw.EntryRow, key: str):
        if self._settings:
            try:
                self._settings.set_string(key, row.get_text().strip())
            except Exception:
                pass

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

    def _on_volume_changed(self, scale: Gtk.Scale) -> None:
        if self._settings:
            try:
                self._settings.set_int("alert-volume", int(scale.get_value()))
            except Exception:
                pass

    def _on_start_sound_changed(self, row: Adw.SwitchRow, _param) -> None:
        if self._settings:
            try:
                self._settings.set_boolean("start-sound", row.get_active())
            except Exception:
                pass

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
