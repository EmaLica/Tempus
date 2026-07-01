import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from .timer import SessionType, TimerState, SESSION_NAMES

OBJECT_PATH = "/io/github/EmaLica/Tempus/Timer"
IFACE = "io.github.EmaLica.Tempus.Timer"

STATE_NAMES = {
    TimerState.IDLE: "idle",
    TimerState.RUNNING: "running",
    TimerState.PAUSED: "paused",
    TimerState.FINISHED: "finished",
}

SESSION_IDS = {
    SessionType.FOCUS: "focus",
    SessionType.SHORT_BREAK: "short-break",
    SessionType.LONG_BREAK: "long-break",
    SessionType.CUSTOM: "custom",
}
SESSION_BY_ID = {v: k for k, v in SESSION_IDS.items()}

_TYPES = {
    "State": "s",
    "SessionType": "s",
    "SessionName": "s",
    "Remaining": "i",
    "Duration": "i",
    "TimeLabel": "s",
    "Progress": "d",
    "Running": "b",
}

INTERFACE_XML = f"""
<node>
  <interface name='{IFACE}'>
    <method name='Start'/>
    <method name='Pause'/>
    <method name='Toggle'/>
    <method name='Reset'/>
    <method name='Skip'/>
    <method name='SetSessionType'>
      <arg type='s' name='session' direction='in'/>
    </method>
    <method name='Present'/>
    <property name='State' type='s' access='read'/>
    <property name='SessionType' type='s' access='read'/>
    <property name='SessionName' type='s' access='read'/>
    <property name='Remaining' type='i' access='read'/>
    <property name='Duration' type='i' access='read'/>
    <property name='TimeLabel' type='s' access='read'/>
    <property name='Progress' type='d' access='read'/>
    <property name='Running' type='b' access='read'/>
  </interface>
</node>
"""


def snapshot(win) -> dict:
    if win is None:
        return {
            "State": "idle",
            "SessionType": "focus",
            "SessionName": "Focus",
            "Remaining": 0,
            "Duration": 0,
            "TimeLabel": "00:00",
            "Progress": 0.0,
            "Running": False,
        }
    t = win.timer
    return {
        "State": STATE_NAMES.get(t.state, "idle"),
        "SessionType": SESSION_IDS.get(t.session_type, "focus"),
        "SessionName": SESSION_NAMES.get(t.session_type, "Focus"),
        "Remaining": int(t.remaining),
        "Duration": int(t.duration),
        "TimeLabel": t.format_time(),
        "Progress": float(t.progress),
        "Running": t.state == TimerState.RUNNING,
    }


def _variant(name, value):
    return GLib.Variant(_TYPES[name], value)


class TimerService:
    def __init__(self, app):
        self._app = app
        self._conn = None
        self._reg_id = 0
        self._node = Gio.DBusNodeInfo.new_for_xml(INTERFACE_XML)

    def register(self, conn):
        self._conn = conn
        self._reg_id = conn.register_object(
            OBJECT_PATH,
            self._node.interfaces[0],
            self._on_method,
            self._on_get,
            None,
        )

    def unregister(self):
        if self._conn and self._reg_id:
            self._conn.unregister_object(self._reg_id)
            self._reg_id = 0

    def _win(self):
        return self._app.get_active_window()

    def _on_get(self, _conn, _sender, _path, _iface, prop):
        return _variant(prop, snapshot(self._win())[prop])

    def _on_method(self, _conn, _sender, _path, _iface, method, params, invocation):
        win = self._win()
        if method == "SetSessionType":
            (sid,) = params.unpack()
            stype = SESSION_BY_ID.get(sid)
            if win and stype:
                win.remote_set_session(stype)
        elif method == "Present":
            if win:
                win.remote_present()
        elif win:
            if method == "Toggle":
                win.remote_toggle()
            elif method == "Start":
                if win.timer.state != TimerState.RUNNING:
                    win.remote_toggle()
            elif method == "Pause":
                if win.timer.state == TimerState.RUNNING:
                    win.remote_toggle()
            elif method == "Reset":
                win.remote_reset()
            elif method == "Skip":
                win.remote_skip()
        invocation.return_value(None)

    def emit_changed(self):
        if not self._conn:
            return
        snap = snapshot(self._win())
        changed = GLib.Variant("a{sv}", {k: _variant(k, v) for k, v in snap.items()})
        self._conn.emit_signal(
            None,
            OBJECT_PATH,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            GLib.Variant.new_tuple(
                GLib.Variant("s", IFACE),
                changed,
                GLib.Variant("as", []),
            ),
        )
