import math
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from .timer import Timer, SESSION_NAMES, SessionType

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

        self.set_title("Tempus")
        self.set_default_size(420, 660)
        self._build_ui()
        self._on_tick()

    def _build_ui(self):
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_vexpand(True)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

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

        toolbar_view.set_content(box)
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

    def _on_tick(self):
        self._time_label.set_label(self.timer.format_time())
        self._drawing.queue_draw()
