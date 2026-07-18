"""L1 — signal extraction from per-frame geometry (blink detection + PERCLOS)."""

from ridewme.calibration import Baseline
from ridewme.config import Tuning
from ridewme.signals import RawFeatures, SignalExtractor

BASE = Baseline(ready=True, ear_open=0.30, closed_ear_threshold=0.216,
                pitch_neutral=0.0, mar_neutral=0.0, samples=50)


def raw(ear, mar=0.0, pitch=0.0):
    return RawFeatures(face_present=True, ear=ear, mar=mar, pitch_deg=pitch)


def test_blink_is_detected():
    ext = SignalExtractor(Tuning())
    now = 0.0
    for _ in range(10):                     # eyes open ~1s
        s = ext.update(raw(0.30), now, BASE)
        now += 0.1
    assert s.eye_closed is False
    ext.update(raw(0.10), now, BASE); now += 0.2   # closed ~200ms
    s = ext.update(raw(0.30), now, BASE)            # reopen -> blink ends
    assert s.blink_rate > 0.0
    assert s.blink_dur_ms > 150.0


def test_sustained_closure_raises_perclos():
    ext = SignalExtractor(Tuning())
    now = 0.0
    for _ in range(30):                     # eyes closed ~3s
        s = ext.update(raw(0.10), now, BASE)
        now += 0.1
    assert s.perclos > 0.8


def test_headnod_and_yawn_are_relative_to_baseline():
    ext = SignalExtractor(Tuning())
    s = ext.update(raw(0.30, mar=0.55, pitch=-18.0), 0.0, BASE)
    assert s.pitch_drop_deg > 15.0          # nodded 18deg below neutral(0)
    assert s.mar_excess > 0.5               # mouth well over neutral(0)
