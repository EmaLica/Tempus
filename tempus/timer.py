from enum import Enum, auto
from gi.repository import GLib


class SessionType(Enum):
    FOCUS = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()
    CUSTOM = auto()


class TimerState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


SESSION_NAMES = {
    SessionType.FOCUS: "Focus",
    SessionType.SHORT_BREAK: "Short Break",
    SessionType.LONG_BREAK: "Long Break",
    SessionType.CUSTOM: "Custom",
}

DEFAULT_DURATIONS = {
    SessionType.FOCUS: 25 * 60,
    SessionType.SHORT_BREAK: 5 * 60,
    SessionType.LONG_BREAK: 15 * 60,
    SessionType.CUSTOM: 10 * 60,
}


class Timer:
    def __init__(self):
        self.state = TimerState.IDLE
        self.session_type = SessionType.FOCUS
        self.durations = dict(DEFAULT_DURATIONS)
        self.duration = self.durations[SessionType.FOCUS]
        self.remaining = self.duration
        self.sessions_completed = 0
        self.sessions_before_long_break = 4
        self._timeout_id = None
        self._tick_callbacks = []
        self._finish_callbacks = []

    def set_session_type(self, session_type: SessionType):
        self._cancel_timeout()
        self.session_type = session_type
        self.duration = self.durations[session_type]
        self.remaining = self.duration
        self.state = TimerState.IDLE
        self._emit_tick()

    def reload_durations(self):
        self.duration = self.durations[self.session_type]
        self.remaining = self.duration
        self._emit_tick()

    def start(self):
        if self.state in (TimerState.IDLE, TimerState.PAUSED):
            self.state = TimerState.RUNNING
            self._timeout_id = GLib.timeout_add_seconds(1, self._tick)

    def pause(self):
        if self.state == TimerState.RUNNING:
            self._cancel_timeout()
            self.state = TimerState.PAUSED

    def reset(self):
        self._cancel_timeout()
        self.remaining = self.duration
        self.state = TimerState.IDLE
        self._emit_tick()

    def _tick(self):
        self.remaining = max(0, self.remaining - 1)
        self._emit_tick()
        if self.remaining <= 0:
            self._finish()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _finish(self):
        self._timeout_id = None
        self.state = TimerState.FINISHED
        if self.session_type == SessionType.FOCUS:
            self.sessions_completed += 1
        for cb in self._finish_callbacks:
            cb()

    def _cancel_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def _emit_tick(self):
        for cb in self._tick_callbacks:
            cb()

    def connect_tick(self, callback):
        self._tick_callbacks.append(callback)

    def connect_finish(self, callback):
        self._finish_callbacks.append(callback)

    @property
    def progress(self):
        if self.duration == 0:
            return 0.0
        return 1.0 - (self.remaining / self.duration)

    def format_time(self) -> str:
        m, s = divmod(self.remaining, 60)
        return f"{m:02d}:{s:02d}"
