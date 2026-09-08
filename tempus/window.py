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

# minuti min/max per tipo di sessione, allineati alle <range> della gschema
DURATION_RANGES: dict[SessionType, tuple[int, int]] = {
    SessionType.FOCUS:       (1, 90),
    SessionType.SHORT_BREAK: (1, 30),
    SessionType.LONG_BREAK:  (1, 60),
    SessionType.CUSTOM:      (1, 120),
}

SETTING_KEYS: dict[SessionType, str] = {
    SessionType.FOCUS:       "focus-duration",
    SessionType.SHORT_BREAK: "short-break-duration",
    SessionType.LONG_BREAK:  "long-break-duration",
    SessionType.CUSTOM:      "custom-duration",
}


class TempusWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timer = Timer()
        self.timer.connect_finish(self._on_finish)
        self._state_cb = None
        self._alert_pipeline = None
        self._alert_uri = None
        self._alert_active = False
        self._scroll_accum = 0.0

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

        stats_btn = Gtk.Button(icon_name="io.github.EmaLica.Tempus-calendar-symbolic")
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

        length_pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        length_pill.add_css_class("linked")
        length_pill.set_halign(Gtk.Align.CENTER)

        # toggle indipendenti (non un gruppo radio): scrollando sul ring il
        # focus può finire su un valore non-preset e allora nessuno dei due
        # dev'essere attivo
        self._focus_length_btns: dict[int, Gtk.ToggleButton] = {}
        self._focus_length_handlers: dict[int, int] = {}
        for minutes in (25, 50):
            btn = Gtk.ToggleButton(label=f"{minutes} min")
            hid = btn.connect("toggled", self._on_focus_length_toggled, minutes)
            self._focus_length_handlers[minutes] = hid
            length_pill.append(btn)
            self._focus_length_btns[minutes] = btn

        self._focus_length_revealer = Gtk.Revealer()
        self._focus_length_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._focus_length_revealer.set_child(length_pill)
        box.append(self._focus_length_revealer)

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

        scroll_ctrl = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll_ctrl.connect("scroll", self._on_ring_scroll)
        overlay.add_controller(scroll_ctrl)

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

        self._skip_btn = Gtk.Button(icon_name="io.github.EmaLica.Tempus-skip-forward-symbolic")
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
        self._sync_focus_length_buttons()
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
            self._stop_alert()
            self._alert_active = False
            self.timer.set_session_type(stype)
            self._focus_length_revealer.set_reveal_child(stype == SessionType.FOCUS)
            self._update_start_icon()
            self._drawing.queue_draw()
            self._on_tick()

    def _on_focus_length_toggled(self, btn: Gtk.ToggleButton, minutes: int):
        if not btn.get_active():
            # un preset non si "spegne" cliccandoci sopra: se è quello corrente
            # lo riaccendiamo, altrimenti era già inattivo e non c'è nulla da fare
            if self._focus_minutes == minutes:
                self._set_focus_btn_silently(minutes, True)
            return
        self._set_focus_duration(minutes)

    def _set_focus_duration(self, minutes: int):
        self._focus_minutes = minutes
        self.timer.durations[SessionType.FOCUS] = minutes * 60
        if self.timer.session_type == SessionType.FOCUS:
            self.timer.reload_durations()
        if self._settings:
            try:
                self._settings.set_int("focus-duration", minutes)
            except Exception:
                pass
        self._sync_focus_length_buttons()
        self._drawing.queue_draw()

    def _set_focus_btn_silently(self, minutes: int, active: bool):
        btn = self._focus_length_btns[minutes]
        hid = self._focus_length_handlers[minutes]
        btn.handler_block(hid)
        btn.set_active(active)
        btn.handler_unblock(hid)

    def _sync_focus_length_buttons(self):
        for minutes, btn in self._focus_length_btns.items():
            want = minutes == self._focus_minutes
            if btn.get_active() != want:
                self._set_focus_btn_silently(minutes, want)

    def _on_ring_scroll(self, _ctrl, _dx, dy):
        # nudge della durata della sessione mostrata sul ring, solo da fermo.
        # su = più tempo, giù = meno; ±1 min per tacca di rotella. i touchpad
        # sparano tanti eventi piccoli, quindi accumuliamo il delta
        if self.timer.state != TimerState.IDLE or self._alert_active:
            return False
        if dy == 0:
            return False
        if (dy > 0) != (self._scroll_accum > 0):
            self._scroll_accum = 0.0
        self._scroll_accum += dy
        step = 0
        while self._scroll_accum >= 1.0:
            step -= 1
            self._scroll_accum -= 1.0
        while self._scroll_accum <= -1.0:
            step += 1
            self._scroll_accum += 1.0
        if step:
            self._nudge_duration(step)
        return True

    def _nudge_duration(self, step_minutes: int):
        stype = self.timer.session_type
        lo, hi = DURATION_RANGES[stype]
        cur = round(self.timer.durations[stype] / 60)
        new = max(lo, min(hi, cur + step_minutes))
        if new == cur:
            return
        if stype == SessionType.FOCUS:
            self._set_focus_duration(new)
            return
        self.timer.durations[stype] = new * 60
        self.timer.reload_durations()
        if self._settings:
            try:
                self._settings.set_int(SETTING_KEYS[stype], new)
            except Exception:
                pass

    def _on_finish(self):
        self._update_start_icon()
        self._refresh_dots()
        self._dnd_set_focus_mode(False)
        self._send_notification()
        looping = self._loop_alert_enabled() and self._play_alert()
        if not looping:
            self._play_sound("finish.mp3")
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
        if looping:
            self._alert_active = True
            self._update_start_icon()
            self._on_tick()
        else:
            self._auto_advance()
        self._drawing.queue_draw()

    def _auto_advance(self):
        if self.timer.session_type == SessionType.FOCUS:
            # una sessione lunga (~50') apre un long break, una corta uno short
            if self._focus_minutes >= 38:
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

    def _loop_alert_enabled(self) -> bool:
        if not self._settings:
            return False
        try:
            return self._settings.get_boolean("loop-alert")
        except Exception:
            return False

    def _play_alert(self) -> bool:
        self._stop_alert()
        path = SOUNDS_DIR / "finish.mp3"
        if not path.exists():
            return False
        vol = 0.7
        try:
            if self._settings:
                vol = self._settings.get_int("alert-volume") / 100.0
        except Exception:
            pass
        try:
            pl = Gst.ElementFactory.make("playbin", None)
            self._alert_uri = path.as_uri()
            pl.set_property("uri", self._alert_uri)
            pl.set_property("volume", vol)
            # loop gapless: riassegniamo l'uri prima che lo stream finisca,
            # così il playbin riparte da capo e l'EOS non arriva mai
            pl.connect("about-to-finish", self._on_alert_about_to_finish)
            bus = pl.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_alert_message)
            pl.set_state(Gst.State.PLAYING)
            self._alert_pipeline = pl
            return True
        except Exception:
            self._alert_pipeline = None
            return False

    def _on_alert_about_to_finish(self, pl):
        if self._alert_uri:
            pl.set_property("uri", self._alert_uri)

    def _on_alert_message(self, _bus, msg):
        if msg.type == Gst.MessageType.EOS and self._alert_pipeline is not None:
            # fallback se about-to-finish non ha rifornito lo stream in tempo:
            # riavvio completo del pipeline
            self._alert_pipeline.set_state(Gst.State.NULL)
            self._alert_pipeline.set_state(Gst.State.PLAYING)
        elif msg.type == Gst.MessageType.ERROR:
            self._stop_alert()

    def _stop_alert(self):
        self._alert_uri = None
        if self._alert_pipeline is not None:
            self._alert_pipeline.set_state(Gst.State.NULL)
            self._alert_pipeline = None

    def _dismiss_alert(self):
        self._stop_alert()
        self._alert_active = False
        self._auto_advance()
        self._update_start_icon()
        self._drawing.queue_draw()

    def _send_notification(self):
        app = self.get_application()
        notif = Gio.Notification.new("Tempus")
        notif.set_body(f"{SESSION_NAMES[self.timer.session_type]} session complete!")
        notif.set_icon(Gio.ThemedIcon.new("io.github.EmaLica.Tempus"))
        app.send_notification("timer-done", notif)

    def _do_start_pause(self):
        if self._alert_active:
            self._dismiss_alert()
            return
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
        self._stop_alert()
        self._alert_active = False
        self._dnd_set_focus_mode(False)
        self.timer.reset()
        self._update_start_icon()
        self._drawing.queue_draw()

    def _do_skip(self):
        self._stop_alert()
        self._alert_active = False
        self._dnd_set_focus_mode(False)
        self.timer.reset()
        self._update_start_icon()
        self._refresh_dots()
        self._auto_advance()
        self._drawing.queue_draw()

    def _update_start_icon(self):
        if self._alert_active:
            icon = "media-playback-stop-symbolic"
        elif self.timer.state == TimerState.RUNNING:
            icon = "media-playback-pause-symbolic"
        else:
            icon = "media-playback-start-symbolic"
        self._start_btn.set_icon_name(icon)
        self._start_btn.set_tooltip_text("Stop the alert" if self._alert_active else "")
        self._push_state()

    def set_state_listener(self, cb):
        self._state_cb = cb

    def _push_state(self):
        if self._state_cb:
            self._state_cb()

    # comandi dal widget nel panel: passano dai metodi normali così DND,
    # suoni, cronologia e dots restano allineati coi pulsanti dell'app
    def remote_toggle(self):
        self._do_start_pause()

    def remote_reset(self):
        self._do_reset()

    def remote_skip(self):
        self._do_skip()

    def remote_set_session(self, stype: SessionType):
        self._session_btns[stype].set_active(True)

    def remote_present(self):
        self.present()

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
        if storage.IN_SANDBOX or self._settings is None:
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
        if storage.IN_SANDBOX:
            return
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
        self._focus_minutes = 25
        try:
            s = Gio.Settings.new("io.github.EmaLica.Tempus")
            self._settings = s
            self._focus_minutes = s.get_int("focus-duration")
            self.timer.durations[SessionType.FOCUS] = self._focus_minutes * 60
            self.timer.durations[SessionType.SHORT_BREAK] = s.get_int("short-break-duration") * 60
            self.timer.durations[SessionType.LONG_BREAK] = s.get_int("long-break-duration") * 60
            self.timer.durations[SessionType.CUSTOM] = s.get_int("custom-duration") * 60
            self.timer.sessions_before_long_break = s.get_int("sessions-before-long-break")
            self.timer.reload_durations()
        except Exception:
            pass

    def _on_tick(self):
        self._push_state()
        self._time_label.set_label(self.timer.format_time())
        self._drawing.queue_draw()

        if self._alert_active:
            self.set_title("Tempus")
            self._session_label.set_label("Time's up")
            return

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
