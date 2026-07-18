"""L3 — the penalty/recovery drowsiness debt. These tests ARE the product claim:
a normal blink barely moves the score, sustained closure climbs to alarm, and the
driver earns the score back to 0 by keeping their eyes open."""

from ridewme.calibration import Baseline
from ridewme.config import Tuning
from ridewme.escalation import Escalator
from ridewme.events import ALARM, WARN
from ridewme.signals import Signals
from ridewme.trust import TrustEngine

BASE = Baseline(ready=True, ear_open=0.30, closed_ear_threshold=0.216,
                pitch_neutral=0.0, mar_neutral=0.0, samples=50)


def sig(ear=0.30, pitch_drop=0.0, mar=0.0):
    return Signals(face_present=True, ear=ear, eye_closed=ear < 0.216, perclos=0.0,
                   blink_rate=10.0, blink_dur_ms=180.0, pitch_drop_deg=pitch_drop, mar_excess=mar)


OPEN, SHUT, SEMI = sig(0.30), sig(0.10), sig(0.24)


def drive(eng, s, seconds, dt=0.05):
    st = None
    for _ in range(int(seconds / dt)):
        st = eng.update(s, BASE, dt)
    return st


def test_open_eyes_stay_at_zero():
    eng = TrustEngine(Tuning())
    assert drive(eng, OPEN, 5.0).score == 0.0


def test_normal_blink_is_negligible():
    eng = TrustEngine(Tuning())
    drive(eng, OPEN, 1.0)
    peak = 0.0
    for _ in range(3):                       # a ~150ms blink
        peak = max(peak, eng.update(SHUT, BASE, 0.05).score)
    assert peak < 14.0                       # never even reaches "notice"
    assert drive(eng, OPEN, 1.0).score < 2.0  # and recovers to baseline


def test_sustained_closure_alarms():
    eng, esc = TrustEngine(Tuning()), Escalator(Tuning())
    e = None
    for _ in range(int(1.8 / 0.05)):         # eyes shut for ~1.8s
        st = eng.update(SHUT, BASE, 0.05)
        e = esc.update(st.score, 0.05, gated=False)
    assert st.score >= 62.0
    assert e.level == ALARM
    assert "eyes" in st.fired


def test_recovery_to_baseline():
    eng = TrustEngine(Tuning())
    for _ in range(int(1.8 / 0.05)):
        st = eng.update(SHUT, BASE, 0.05)
    assert st.score >= 62.0
    assert drive(eng, OPEN, 5.0).score < 3.0   # eyes open -> debt paid back to 0


def test_semi_closed_is_penalized():
    eng, esc = TrustEngine(Tuning()), Escalator(Tuning())
    e = None
    for _ in range(int(2.5 / 0.05)):         # droopy half-closed eyes
        st = eng.update(SEMI, BASE, 0.05)
        e = esc.update(st.score, 0.05, gated=False)
    assert st.score >= 38.0
    assert e.level in (WARN, ALARM)


def test_head_nod_adds_penalty():
    eng = TrustEngine(Tuning())
    st = drive(eng, sig(ear=0.30, pitch_drop=25.0), 3.0)   # eyes open but nodding
    assert st.score > 30.0
    assert "head_nod" in st.fired


def test_alarm_intensity_grows_with_depth():
    esc = Escalator(Tuning())
    shallow = esc.update(63.0, 0.05, gated=False)     # just over alarm
    deep = Escalator(Tuning()).update(98.0, 0.05, gated=False)
    assert deep.audio_intensity > shallow.audio_intensity
