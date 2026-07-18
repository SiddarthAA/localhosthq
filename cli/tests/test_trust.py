"""L3 — the moat. These tests ARE the product claim: a lone cue is a whisper,
corroboration + persistence unlock a real alarm, and recovery backs off."""

from ridewme.calibration import Baseline
from ridewme.config import Tuning
from ridewme.escalation import Escalator
from ridewme.events import ALARM, AWAKE, WARN
from ridewme.signals import Signals
from ridewme.trust import TrustEngine

BASE = Baseline(ready=True, ear_open=0.30, closed_ear_threshold=0.216,
                pitch_neutral=0.0, mar_neutral=0.0, samples=50)


def sig(perclos=0.0, blink_ms=180.0, pitch_drop=0.0, mar=0.0):
    return Signals(face_present=True, ear=0.3, eye_closed=perclos > 0.5,
                   perclos=perclos, blink_rate=10.0, blink_dur_ms=blink_ms,
                   pitch_drop_deg=pitch_drop, mar_excess=mar)


def drive(engine, s, seconds, dt=0.1):
    st = None
    for _ in range(int(seconds / dt)):
        st = engine.update(s, BASE, dt)
    return st


def test_lone_yawn_is_a_whisper():
    """A single active cue (yawn) never escalates past a whisper."""
    eng, esc = TrustEngine(Tuning()), Escalator(Tuning())
    st = None
    for _ in range(400):  # 40s of nothing but yawning
        st = eng.update(sig(mar=1.0), BASE, 0.1)
        e = esc.update(st.score, 0.1, gated=False)
    assert st.agree_count == 1
    assert st.score < 45.0                      # below WARN
    assert e.level in (AWAKE, "notice")         # never WARN/ALARM


def test_lone_perclos_can_warn_but_never_alarm():
    """Sustained eye-closure (microsleep) is dangerous alone — but capped below alarm."""
    eng, esc = TrustEngine(Tuning()), Escalator(Tuning())
    e = None
    for _ in range(400):
        st = eng.update(sig(perclos=0.6), BASE, 0.1)   # strong lone PERCLOS
        e = esc.update(st.score, 0.1, gated=False)
    assert st.agree_count == 1
    assert e.level == WARN
    assert e.level != ALARM


def test_corroboration_unlocks_alarm():
    """PERCLOS + long blinks + head-nod agreeing and persisting => a real alarm."""
    eng, esc = TrustEngine(Tuning()), Escalator(Tuning())
    e = None
    for _ in range(400):
        st = eng.update(sig(perclos=0.6, blink_ms=500.0, pitch_drop=25.0), BASE, 0.1)
        e = esc.update(st.score, 0.1, gated=False)
    assert st.agree_count >= 3
    assert st.score > 72.0
    assert e.level == ALARM


def test_persistence_is_not_instant():
    """The integrator must not trip instantly — one second in, it's nowhere near alarm."""
    eng = TrustEngine(Tuning())
    one_sec = drive(eng, sig(perclos=0.6, blink_ms=500.0, pitch_drop=25.0), 1.0)
    assert one_sec.score < 45.0     # still climbing, not an instant klaxon
    full = drive(eng, sig(perclos=0.6, blink_ms=500.0, pitch_drop=25.0), 30.0)
    assert full.score > 72.0        # given time, it gets there


def test_recovery_backs_off():
    eng, esc = TrustEngine(Tuning()), Escalator(Tuning())
    for _ in range(400):            # drive to alarm
        st = eng.update(sig(perclos=0.6, blink_ms=500.0, pitch_drop=25.0), BASE, 0.1)
        e = esc.update(st.score, 0.1, gated=False)
    assert e.level == ALARM
    for _ in range(600):            # then quiet -> recover
        st = eng.update(sig(), BASE, 0.1)
        e = esc.update(st.score, 0.1, gated=False)
    assert e.level == AWAKE
    assert st.score < 12.0
