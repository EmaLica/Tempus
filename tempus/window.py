import math
import time
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Adw, Gio, Gst, GLib

Gst.init(None)

from .timer import Timer, SESSION_NAMES, SessionType, TimerState
from .todo import TodoPanel
from .preferences import TempusPreferences
from .stats import StatsPanel
from . import storage

RING_SIZE = 224
RING_LINE = 10

SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"

SESSION_COLORS: dict[SessionType, tuple[float, float, float]] = {
    SessionType.FOCUS:       (0.847, 0.169, 0.169),
    SessionType.SHORT_BREAK: (0.180, 0.718, 0.392),
    SessionType.LONG_BREAK:  (0.204, 0.522, 0.894),
    SessionType.CUSTOM:      (0.612, 0.310, 0.831),
}


class TempusWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timer = Timer()
        self.timer.connect_finish(self._on_finish)

        self.set_title("Tempus")
        self.set_default_size(420, 660)
        self._settings: Gio.Settings | None = None
        self._restore_dnd_if_crashed()
        self._load_settings()
        self._build_ui()
        self.timer.connect_tick(self._on_tick)
        self._on_tick()

    def _build_ui(self):
        self._nav = Adw.NavigationView()
        self.set_content(self._nav)

        main_toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        stats_btn = Gtk.Button(icon_name="x-office-calendar-symbolic")
        stats_btn.set_tooltip_text("Today's focus stats")
        stats_btn.connect("clicked", self._on_stats_clicked)
        header.pack_start(stats_btn)

        self._todo_btn = Gtk.ToggleButton(icon_name="view-list-symbolic")
        self._todo_btn.set_tooltip_text("Toggle task list")
        self._todo_btn.connect("toggled", self._on_todo_toggled)
        header.pack_end(self._todo_btn)

        menu = Gio.Menu()
        menu.append("Preferences", "win.preferences")
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)

        pref_action = Gio.SimpleAction.new("preferences", None)
        pref_action.connect("activate", self._on_preferences)
        self.add_action(pref_action)

        main_toolbar.add_top_bar(header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_vexpand(True)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        pill.add_css_class("linked")
        pill.set_halign(Gtk.Align.CENTER)

        self._session_btns: dict[SessionType, Gtk.ToggleButton] = {}
        first = None
        for stype, label in SESSION_NAMES.items():
            btn = Gtk.ToggleButton(label=label)
            if first is None:
                first = btn
            else:
                btn.set_group(first)
            btn.connect("toggled", self._on_session_toggled, stype)
            pill.append(btn)
            self._session_btns[stype] = btn
        box.append(pill)

        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)
        overlay.set_vexpand(True)

        self._drawing = Gtk.DrawingArea()
        self._drawing.set_size_request(RING_SIZE, RING_SIZE)
        self._drawing.set_draw_func(self._draw_ring)
        overlay.set_child(self._drawing)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)

        self._time_label = Gtk.Label()
        self._time_label.add_css_class("title-1")
        center.append(self._time_label)

        self._session_label = Gtk.Label(label="Focus")
        self._session_label.add_css_class("caption-heading")
        self._session_label.add_css_class("dim-label")
        center.append(self._session_label)

        overlay.add_overlay(center)
        box.append(overlay)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        controls.set_halign(Gtk.Align.CENTER)

        self._reset_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self._reset_btn.add_css_class("circular")
        self._reset_btn.set_tooltip_text("Reset")
        self._reset_btn.connect("clicked", lambda *_: self._do_reset())
        controls.append(self._reset_btn)

        self._start_btn = Gtk.Button()
        self._start_btn.add_css_class("circular")
        self._start_btn.add_css_class("suggested-action")
        self._start_btn.set_size_request(64, 64)
        self._start_btn.connect("clicked", lambda *_: self._do_start_pause())
        self._update_start_icon()
        controls.append(self._start_btn)

        self._skip_btn = Gtk.Button(icon_name="media-skip-forward-symbolic")
        self._skip_btn.add_css_class("circular")
        self._skip_btn.set_tooltip_text("Skip session")
        self._skip_btn.connect("clicked", lambda *_: self._do_skip())
        controls.append(self._skip_btn)

        box.append(controls)

        self._dots_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._dots_box.set_halign(Gtk.Align.CENTER)
        self._refresh_dots()
        box.append(self._dots_box)

        body.append(box)
        body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        self._todo_revealer = Gtk.Revealer()
        self._todo_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._todo_revealer.set_reveal_child(False)
        self._todo_panel = TodoPanel()
        self._todo_panel.set_size_request(-1, 300)
        self._todo_revealer.set_child(self._todo_panel)
        body.append(self._todo_revealer)

        main_toolbar.set_content(body)
        self._session_btns[SessionType.FOCUS].set_active(True)

        main_page = Adw.NavigationPage.new(main_toolbar, "Tempus")
        self._nav.add(main_page)

        stats_toolbar = Adw.ToolbarView()
        stats_header = Adw.HeaderBar()
        stats_toolbar.add_top_bar(stats_header)

        self._stats_panel = StatsPanel()
        stats_toolbar.set_content(self._stats_panel)

        self._stats_page = Adw.NavigationPage.new(stats_toolbar, "Today")
        self._stats_page.set_title("Today")
        self._nav.add(self._stats_page)

    def _draw_ring(self, _area, cr, width, height):
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - RING_LINE - 4

        cr.set_line_width(RING_LINE)
        cr.set_line_cap(1)

        cr.set_source_rgba(0.5, 0.5, 0.5, 0.15)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()

        progress = self.timer.progress
        if progress > 0.001:
            r, g, b = SESSION_COLORS[self.timer.session_type]
            cr.set_source_rgb(r, g, b)
            start = -math.pi / 2
            cr.arc(cx, cy, radius, start, start + progress * 2 * math.pi)
            cr.stroke()

    def _on_session_toggled(self, btn: Gtk.ToggleButton, stype: SessionType):
        if btn.get_active():
            self.timer.set_session_type(stype)
            self._update_start_icon()
            self._drawing.queue_draw()
            self._on_tick()

    def _on_finish(self):
        self._update_start_icon()
        self._refresh_dots()
        self._dnd_set_focus_mode(False)
        self._play_sound("finish.mp3")
        self._send_notification()
        if self.timer.session_type == SessionType.FOCUS:
            active_item = self._todo_panel.get_active_item()
            entry: dict = {
                "ts": int(time.time()),
                "session_type": "focus",
                "duration": self.timer.duration,
            }
            if active_item:
                entry["task_id"] = active_item.id
            if active_item and active_item.subject:
                entry["subject"] = active_item.subject
            storage.append_history(entry)
            if active_item:
                self._todo_panel.add_pomodoro(active_item.id)
        self._auto_advance()
        self._drawing.queue_draw()

    def _auto_advance(self):
        if self.timer.session_type == SessionType.FOCUS:
            completed = self.timer.sessions_completed
            if completed > 0 and completed % self.timer.sessions_before_long_break == 0:
                self._session_btns[SessionType.LONG_BREAK].set_active(True)
            else:
                self._session_btns[SessionType.SHORT_BREAK].set_active(True)
        else:
            self._session_btns[SessionType.FOCUS].set_active(True)

    def _play_sound(self, filename):
        path = SOUNDS_DIR / filename
        if not path.exists():
            return
        vol = 0.7
        try:
            if self._settings:
                vol = self._settings.get_int("alert-volume") / 100.0
        except Exception:
            pass
        try:
            pl = Gst.ElementFactory.make("playbin", None)
            pl.set_property("uri", path.as_uri())
            pl.set_property("volume", vol)
            pl.set_state(Gst.State.PLAYING)
            bus = pl.get_bus()
            bus.add_signal_watch()
            # il closure su pl lo tiene vivo finché il bus watch è attivo
            bus.connect(
                "message",
                lambda _, m, p: p.set_state(Gst.State.NULL)
                if m.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR) else None,
                pl,
            )
        except Exception:
            pass

    def _send_notification(self):
        app = self.get_application()
        notif = Gio.Notification.new("Tempus")
        notif.set_body(f"{SESSION_NAMES[self.timer.session_type]} session complete!")
        notif.set_icon(Gio.ThemedIcon.new("io.github.EmaLica.Tempus"))
        app.send_notification("timer-done", notif)

    def _do_start_pause(self):
        if self.timer.state == TimerState.RUNNING:
            self.timer.pause()
            if self.timer.session_type == SessionType.FOCUS:
                self._dnd_set_focus_mode(False)
        else:
            # solo su avvio da fermo, non sul resume da pausa
            fresh = self.timer.state == TimerState.IDLE
            self.timer.start()
            if fresh and self._start_sound_enabled():
                self._play_sound("start.mp3")
            if self.timer.session_type == SessionType.FOCUS:
                self._dnd_set_focus_mode(True)
        self._update_start_icon()

    def _start_sound_enabled(self) -> bool:
        if not self._settings:
            return True
        try:
            return self._settings.get_boolean("start-sound")
        except Exception:
            return True

    def _do_reset(self):
        self._dnd_set_focus_mode(False)
        self.timer.reset()
        self._update_start_icon()
        self._drawing.queue_draw()

    def _do_skip(self):
        self._dnd_set_focus_mode(False)
        self.timer.reset()
        self._update_start_icon()
        self._refresh_dots()
        self._auto_advance()
        self._drawing.queue_draw()

    def _update_start_icon(self):
        icon = (
            "media-playback-pause-symbolic"
            if self.timer.state == TimerState.RUNNING
            else "media-playback-start-symbolic"
        )
        self._start_btn.set_icon_name(icon)

    def _refresh_dots(self):
        child = self._dots_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._dots_box.remove(child)
            child = nxt

        done = self.timer.sessions_completed % self.timer.sessions_before_long_break
        for i in range(self.timer.sessions_before_long_break):
            dot = Gtk.Label()
            if i < done:
                r, g, b = SESSION_COLORS[SessionType.FOCUS]
                dot.set_markup(
                    f'<span color="#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}">●</span>'
                )
            else:
                dot.set_markup('<span color="#808080">○</span>')
            self._dots_box.append(dot)

    def _on_preferences(self, *_):
        prefs = TempusPreferences(timer=self.timer, transient_for=self)
        prefs.present()

    def _on_stats_clicked(self, _btn) -> None:
        self._stats_panel.refresh()
        self._nav.push(self._stats_page)

    def _dnd_set_focus_mode(self, entering: bool) -> None:
        if self._settings is None:
            return
        try:
            if not self._settings.get_boolean("dnd-during-focus"):
                return
        except Exception:
            return

        try:
            notif = Gio.Settings.new("org.gnome.desktop.notifications")
            lock = storage.DATA_DIR / "dnd.lock"
            if entering:
                prev = notif.get_boolean("show-banners")
                lock.parent.mkdir(parents=True, exist_ok=True)
                lock.write_text("true" if prev else "false", encoding="utf-8")
                notif.set_boolean("show-banners", False)
            else:
                if lock.exists():
                    prev_str = lock.read_text(encoding="utf-8").strip()
                    notif.set_boolean("show-banners", prev_str == "true")
                    lock.unlink()
        except Exception:
            pass

    def _restore_dnd_if_crashed(self) -> None:
        try:
            lock = storage.DATA_DIR / "dnd.lock"
            if lock.exists():
                prev_str = lock.read_text(encoding="utf-8").strip()
                notif = Gio.Settings.new("org.gnome.desktop.notifications")
                notif.set_boolean("show-banners", prev_str == "true")
                lock.unlink()
        except Exception:
            pass

    def _on_todo_toggled(self, btn: Gtk.ToggleButton):
        self._todo_revealer.set_reveal_child(btn.get_active())

    def _load_settings(self):
        try:
            s = Gio.Settings.new("io.github.EmaLica.Tempus")
            self._settings = s
            self.timer.durations[SessionType.FOCUS] = s.get_int("focus-duration") * 60
            self.timer.durations[SessionType.SHORT_BREAK] = s.get_int("short-break-duration") * 60
            self.timer.durations[SessionType.LONG_BREAK] = s.get_int("long-break-duration") * 60
            self.timer.durations[SessionType.CUSTOM] = s.get_int("custom-duration") * 60
            self.timer.sessions_before_long_break = s.get_int("sessions-before-long-break")
            self.timer.reload_durations()
        except Exception:
            pass

    def _on_tick(self):
        self._time_label.set_label(self.timer.format_time())
        self._drawing.queue_draw()

        if self.timer.state == TimerState.RUNNING or self.timer.state == TimerState.PAUSED:
            self.set_title(f"{self.timer.format_time()} · {SESSION_NAMES[self.timer.session_type]}")
        else:
            self.set_title("Tempus")

        if self.timer.session_type == SessionType.FOCUS:
            active = self._todo_panel.get_active_item()
            if active:
                text = active.text
                truncated = text[:22] + "…" if len(text) > 22 else text
                self._session_label.set_label(truncated)
                return
        self._session_label.set_label(SESSION_NAMES[self.timer.session_type])
