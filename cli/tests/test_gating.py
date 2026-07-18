"""L4 — context gating. A parked vehicle is silent even under a real decision."""

from ridewme.config import Tuning
from ridewme.escalation import Escalator
from ridewme.events import ALARM, AWAKE
from ridewme.gating import ContextGate


def test_gate_maps_moving_flag():
    # Seam 1: the gate takes a `moving` bool (fail-safe lives in MotionState).
    g = ContextGate()
    assert g.evaluate(True) == (False, None)            # moving -> not gated
    assert g.evaluate(False) == (True, "not_moving")    # not moving -> gated


def test_gated_alarm_is_silenced_but_still_reported():
    esc = Escalator(Tuning())
    e = esc.update(score=95.0, dt=0.1, gated=True)
    # the decision still stands (fleet sees it) ...
    assert e.level == ALARM
    assert e.gated is True
    # ... but the in-cabin output is suppressed.
    assert e.effective_level == AWAKE
    assert e.audio_intensity == 0.0


def test_ungated_alarm_sounds():
    esc = Escalator(Tuning())
    e = esc.update(score=95.0, dt=0.1, gated=False)
    assert e.level == ALARM
    assert e.effective_level == ALARM
