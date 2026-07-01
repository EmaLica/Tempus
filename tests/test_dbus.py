from tempus.timer import Timer, SessionType, TimerState


class FakeWindow:
    def __init__(self, timer):
        self.timer = timer


def test_snapshot_none_window_is_idle():
    from tempus import dbus
    snap = dbus.snapshot(None)
    assert snap["State"] == "idle"
    assert snap["Running"] is False
    assert snap["TimeLabel"] == "00:00"
    assert snap["Duration"] == 0


def test_snapshot_fresh_focus_timer():
    from tempus import dbus
    snap = dbus.snapshot(FakeWindow(Timer()))
    assert snap["State"] == "idle"
    assert snap["SessionType"] == "focus"
    assert snap["SessionName"] == "Focus"
    assert snap["Remaining"] == 25 * 60
    assert snap["Duration"] == 25 * 60
    assert snap["TimeLabel"] == "25:00"
    assert snap["Progress"] == 0.0
    assert snap["Running"] is False


def test_snapshot_running_reports_progress():
    from tempus import dbus
    t = Timer()
    t.state = TimerState.RUNNING
    t.remaining = 900  # 15:00 left of a 25:00 focus
    snap = dbus.snapshot(FakeWindow(t))
    assert snap["State"] == "running"
    assert snap["Running"] is True
    assert snap["TimeLabel"] == "15:00"
    assert abs(snap["Progress"] - (1 - 900 / 1500)) < 1e-9


def test_snapshot_maps_every_session_type():
    from tempus import dbus
    for stype in SessionType:
        t = Timer()
        t.set_session_type(stype)
        snap = dbus.snapshot(FakeWindow(t))
        assert snap["SessionType"] == dbus.SESSION_IDS[stype]
        assert dbus.SESSION_BY_ID[snap["SessionType"]] is stype


def test_session_id_roundtrip_is_total():
    from tempus import dbus
    assert set(dbus.SESSION_IDS.values()) == set(dbus.SESSION_BY_ID.keys())
    assert len(dbus.SESSION_IDS) == len(SessionType)
