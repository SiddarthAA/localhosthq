"""Crash engine — the intelligence is the fusion heuristic (design §1-2). These
tests ARE the product claim: a pothole or a hard stop must NOT confirm; a real
impact must; parked jolts die at the pre-gate; the driver can always cancel; and
a car that drives off de-escalates."""

from ridewme import events as E
from ridewme.config import Tuning
from ridewme.crash import CrashEngine
from ridewme.motion import MotionState


def fast_tuning():
    t = Tuning()
    t.crash_l2_window_s = 0.4          # shorten windows so tests run fast
    t.crash_l3_window_s = 1.0
    t.crash_l3_window_severe_s = 0.6
    t.deescalate_sustained_s = 0.5
    t.crash_cooldown_s = 0.3
    return t


def build():
    t = fast_tuning()
    motion = MotionState(t.moving_mps, t.motion_stale_s)
    emitted: list[dict] = []
    eng = CrashEngine(t, motion, "s-test",
                      emit_fn=lambda p, ts: emitted.append(p),
                      fatigue_fn=lambda now: {"was_elevated": False, "recent_max_score": 0.0},
                      alarm_fn=lambda a, i: None)
    return eng, emitted


def pkt(speed=12.0, accelG=(0.0, 0.0, 9.8), gyro=(1.0, 1.0, 1.0), gps=True):
    p = {"accelG": {"x": accelG[0], "y": accelG[1], "z": accelG[2]},
         "gyro": {"alpha": gyro[0], "beta": gyro[1], "gamma": gyro[2]}}
    p["gps"] = {"lat": 12.9, "lon": 77.5, "speed": speed} if gps else {}
    return p


def run(eng, samples):
    for ts, p in samples:
        eng.ingest(p, ts)
        eng.tick(ts)


def _series(pre_speed=12.0, impact=None, post_speed=0.0, gps=True,
            pre_s=1.0, impact_n=3, post_s=1.8, dt=0.02):
    """moving -> (optional impact) -> settled. Returns [(ts, packet), ...]."""
    out, ts = [], 0.0
    while ts < pre_s:
        out.append((ts, pkt(speed=pre_speed, gps=gps))); ts += dt
    if impact is not None:
        for _ in range(impact_n):
            out.append((ts, pkt(speed=post_speed, accelG=impact[0], gyro=impact[1], gps=gps))); ts += dt
    end = ts + post_s
    while ts < end:
        out.append((ts, pkt(speed=post_speed, gps=gps))); ts += dt
    return out


IMPACT = ((70.0, 20.0, 9.8), (260.0, 210.0, 30.0))    # ~7.5g peak, 2 gyro axes hot


def test_real_crash_confirms():
    eng, emitted = build()
    run(eng, _series(impact=IMPACT, post_speed=0.0))
    statuses = [e["status"] for e in emitted]
    assert E.UNCONFIRMED in statuses and E.CONFIRMED in statuses
    unc = emitted[0]
    assert unc["status"] == E.UNCONFIRMED
    assert unc["severity"] == E.SEVERE
    assert set(unc["signals_fired"]) == {"accel_jerk", "gyro"}   # accel + gyro only (no GPS)
    assert emitted[-1]["status"] == E.CONFIRMED
    assert emitted[-1]["final_motion"] == "stopped"


def test_pothole_does_not_confirm():
    # sharp jolt (accel + jerk) but NO rotation, NO speed drop -> only 1 signal
    eng, emitted = build()
    run(eng, _series(pre_speed=12.0, impact=((40.0, 0.0, 9.8), (1.0, 1.0, 1.0)), post_speed=12.0))
    assert emitted == []


def test_gradual_stop_does_not_confirm():
    # a smooth high-g decel to a stop: accel rises and falls gradually (LOW jerk) while
    # speed bleeds off -> accel_jerk never fires -> not a crash.
    eng, emitted = build()
    ts, out = 0.0, []
    while ts < 1.0:
        out.append((ts, pkt(speed=12.0))); ts += 0.02
    for i in range(150):                        # smooth 0->~3g->0 triangle over 3s (jerk ~2 g/s)
        frac = i / 150.0
        g = 3.0 * (1 - abs(2 * frac - 1))
        out.append((ts, pkt(speed=12.0 * (1 - frac), accelG=(g * 9.8, 0.0, 9.8)))); ts += 0.02
    while ts < 6.0:
        out.append((ts, pkt(speed=0.0))); ts += 0.02
    run(eng, out)
    assert all(e["status"] != E.CONFIRMED for e in emitted)
    assert all("accel_jerk" not in e.get("signals_fired", []) for e in emitted)


def test_failopen_no_gps_confirms_on_accel_plus_gyro():
    eng, emitted = build()
    run(eng, _series(impact=IMPACT, gps=False))     # no GPS -> pre-gate fails open
    unc = [e for e in emitted if e["status"] == E.UNCONFIRMED]
    assert unc, "should confirm on accel+gyro alone when GPS is absent"
    assert set(unc[0]["signals_fired"]) >= {"accel_jerk", "gyro"}
    assert "speed_drop" not in unc[0]["signals_fired"]


def test_driver_cancel():
    eng, emitted = build()
    # feed up to just after unconfirmed, then cancel
    samples = _series(impact=IMPACT, post_speed=0.0)
    for ts, p in samples:
        eng.ingest(p, ts)
        eng.tick(ts)
        if eng.active_incident is not None:
            assert eng.cancel(ts) is True
            break
    statuses = [e["status"] for e in emitted]
    assert E.UNCONFIRMED in statuses and E.CANCELLED in statuses
    assert E.CONFIRMED not in statuses
    assert emitted[-1]["reason"] == E.REASON_DRIVER


def test_simulate_impact_inject():
    eng, emitted = build()
    eng.simulate_impact(now=5.0)
    assert emitted and emitted[0]["status"] == E.UNCONFIRMED
    assert emitted[0]["severity"] == E.SEVERE
    for k in range(200):                     # advance past the window -> confirm
        eng.tick(5.0 + 0.6 + k * 0.02)
    assert emitted[-1]["status"] == E.CONFIRMED


def test_fatigue_context_attached():
    t = fast_tuning()
    motion = MotionState(t.moving_mps, t.motion_stale_s)
    emitted: list[dict] = []
    eng = CrashEngine(t, motion, "s-test", emit_fn=lambda p, ts: emitted.append(p),
                      fatigue_fn=lambda now: {"was_elevated": True, "recent_max_score": 80.0,
                                              "elevated_seconds": 40.0, "sampled_over_minutes": 5.0})
    run(eng, _series(impact=IMPACT, post_speed=0.0))
    assert emitted[0]["fatigue_context"]["was_elevated"] is True
    assert emitted[0]["fatigue_context"]["recent_max_score"] == 80.0
