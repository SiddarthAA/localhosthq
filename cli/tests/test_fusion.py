"""Crash fusion — fire only when >=2 of 3 corroborate; lifecycle gated by a
driver-cancel countdown (we don't call 112 on a pothole)."""

from ridewme.config import Tuning
from ridewme.events import CANCELLED, CONFIRMED, DETECTED, MODERATE
from ridewme.fusion import CrashFusion, IncidentManager


def rest(speed=12.0):
    return {"accelG": {"x": 0.0, "y": 0.0, "z": 9.8},
            "gyro": {"alpha": 1.0, "beta": 1.0, "gamma": 1.0},
            "gps": {"lat": 1.0, "lon": 2.0, "speed": speed}}


def crash(speed=0.0):
    return {"accelG": {"x": 40.0, "y": 10.0, "z": 9.8},       # ~4.3g
            "gyro": {"alpha": 250.0, "beta": 50.0, "gamma": 30.0},  # large rotation
            "gps": {"lat": 1.0, "lon": 2.0, "speed": speed}}


def accel_only():
    return {"accelG": {"x": 40.0, "y": 10.0, "z": 9.8},
            "gyro": {"alpha": 1.0, "beta": 1.0, "gamma": 1.0},   # no rotation
            "gps": {"lat": 1.0, "lon": 2.0, "speed": 12.0}}      # no speed drop


def _warmup(f, now):
    for _ in range(20):
        f.update(rest(), now)
        now += 0.05
    return now


def test_single_signal_does_not_fire():
    f = CrashFusion(Tuning())
    now = _warmup(f, 0.0)
    assert f.update(accel_only(), now) is None   # only 1 of 3


def test_two_of_three_fires_with_severity():
    f = CrashFusion(Tuning())
    now = _warmup(f, 0.0)
    sig = f.update(crash(), now)                  # accel + rotation + speed drop
    assert sig is not None
    assert len(sig.reasons) >= 2
    assert sig.severity == MODERATE               # ~4.3g
    assert sig.location is not None


def test_incident_lifecycle_confirm():
    t = Tuning()
    f = CrashFusion(t)
    now = _warmup(f, 100.0)
    sig = f.update(crash(), now)
    im = IncidentManager(t, "s-test")
    u = im.on_signal(sig, 100.0)
    assert u.status == DETECTED
    assert im.tick(105.0) is None                 # still inside the cancel window
    u2 = im.tick(100.0 + t.cancel_window_s + 0.1)
    assert u2.status == CONFIRMED


def test_incident_lifecycle_cancel():
    t = Tuning()
    f = CrashFusion(t)
    now = _warmup(f, 200.0)
    sig = f.update(crash(), now)
    im = IncidentManager(t, "s-test")
    im.on_signal(sig, 200.0)
    c = im.cancel(201.0)
    assert c.status == CANCELLED
    assert im.tick(200.0 + t.cancel_window_s + 5.0) is None   # cancelled -> no dispatch
