import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from .timer import Timer


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

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_vexpand(True)
        box.set_margin_top(32)
        box.set_margin_bottom(32)
        box.set_margin_start(24)
        box.set_margin_end(24)

        self._time_label = Gtk.Label()
        self._time_label.add_css_class("title-1")
        box.append(self._time_label)

        toolbar_view.set_content(box)
        self.set_content(toolbar_view)

    def _on_tick(self):
        self._time_label.set_label(self.timer.format_time())
