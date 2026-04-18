import math
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from .timer import Timer, SESSION_NAMES, SessionType, TimerState
from .todo import TodoPanel

RING_SIZE = 224
RING_LINE = 10

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
        self.timer.connect_tick(self._on_tick)
        self.timer.connect_finish(self._on_finish)

        self.set_title("Tempus")
        self.set_default_size(420, 660)
        self._build_ui()
        self._on_tick()

    def _build_ui(self):
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()

        self._todo_btn = Gtk.ToggleButton(icon_name="view-list-symbolic")
        self._todo_btn.set_tooltip_text("Toggle Todo list")
        self._todo_btn.connect("toggled", self._on_todo_toggled)
        header.pack_end(self._todo_btn)

        toolbar_view.add_top_bar(header)

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
        self._session_btns[SessionType.FOCUS].set_active(True)
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

        toolbar_view.set_content(body)
        self.set_content(toolbar_view)

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
            self._session_label.set_text(SESSION_NAMES[stype])
            self._update_start_icon()
            self._drawing.queue_draw()

    def _on_finish(self):
        self._update_start_icon()
        self._refresh_dots()
        self._send_notification()
        self._auto_advance()
        self._drawing.queue_draw()

    def _auto_advance(self):
        if self.timer.session_type == SessionType.FOCUS:
            if self.timer.sessions_completed % self.timer.sessions_before_long_break == 0:
                self._session_btns[SessionType.LONG_BREAK].set_active(True)
            else:
                self._session_btns[SessionType.SHORT_BREAK].set_active(True)
        else:
            self._session_btns[SessionType.FOCUS].set_active(True)

    def _send_notification(self):
        app = self.get_application()
        notif = Gio.Notification.new("Tempus")
        notif.set_body(f"{SESSION_NAMES[self.timer.session_type]} session complete!")
        notif.set_icon(Gio.ThemedIcon.new("io.github.EmaLica.Tempus"))
        app.send_notification("timer-done", notif)

    def _do_start_pause(self):
        if self.timer.state == TimerState.RUNNING:
            self.timer.pause()
        else:
            self.timer.start()
        self._update_start_icon()

    def _do_reset(self):
        self.timer.reset()
        self._update_start_icon()
        self._drawing.queue_draw()

    def _do_skip(self):
        self.timer.reset()
        self._on_finish()

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

    def _on_todo_toggled(self, btn: Gtk.ToggleButton):
        self._todo_revealer.set_reveal_child(btn.get_active())

    def _load_settings(self):
        try:
            s = Gio.Settings.new("io.github.EmaLica.Tempus")
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
