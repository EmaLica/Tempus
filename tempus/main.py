import sys
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk

from .window import TempusWindow
from .dbus import TimerService


class TempusApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.EmaLica.Tempus",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._dbus = None
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<primary>q"])

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        self.add_action(prefs_action)
        self.set_accels_for_action("app.preferences", ["<primary>comma"])

    def do_dbus_register(self, connection, object_path):
        Adw.Application.do_dbus_register(self, connection, object_path)
        self._dbus = TimerService(self)
        try:
            self._dbus.register(connection)
        except Exception:
            self._dbus = None
        return True

    def do_dbus_unregister(self, connection, object_path):
        if self._dbus:
            self._dbus.unregister()
            self._dbus = None
        Adw.Application.do_dbus_unregister(self, connection, object_path)

    def do_activate(self):
        icons_dir = Path(__file__).resolve().parent.parent / "data" / "icons"
        if icons_dir.is_dir():
            theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            theme.add_search_path(str(icons_dir))

        win = self.props.active_window
        if not win:
            win = TempusWindow(application=self)
            if self._dbus:
                win.set_state_listener(self._dbus.emit_changed)
                self._dbus.emit_changed()
        win.present()

    def _on_about(self, *_):
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="Tempus",
            application_icon="io.github.EmaLica.Tempus",
            developer_name="EmaLica",
            version="0.6.0",
            website="https://github.com/EmaLica/Tempus",
            issue_url="https://github.com/EmaLica/Tempus/issues",
            license_type=Gtk.License.GPL_3_0,
            copyright="© 2026 EmaLica",
            comments="A focused Pomodoro timer for GNOME",
        )
        about.present()

    def _on_preferences(self, *_):
        win = self.props.active_window
        from .preferences import TempusPreferences
        prefs = TempusPreferences(
            transient_for=win,
            timer=win.timer if win else None,
        )
        prefs.present()


def main():
    app = TempusApplication()
    return app.run(sys.argv)
