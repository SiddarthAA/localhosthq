"""Seam 1 — VehicleMotion, with the all-important fail-safe (design §4)."""

from ridewme.motion import MotionState


def test_moving_and_stationary():
    ms = MotionState(moving_mps=2.0)
    ms.update(speed_mps=10.0, gps_available=True, now=100.0)
    assert ms.get().moving is True
    assert ms.moving_for_gate(100.1) is True
    assert ms.stationary_confident(100.1) is False

    ms.update(speed_mps=0.0, gps_available=True, now=101.0)
    assert ms.moving_for_gate(101.1) is False        # fresh fix says stopped
    assert ms.stationary_confident(101.1) is True


def test_failsafe_no_gps_assumes_moving():
    ms = MotionState(moving_mps=2.0)
    ms.update(speed_mps=None, gps_available=False, now=100.0)
    # never suppress a real fatigue alert when we can't confirm stopped
    assert ms.moving_for_gate(100.1) is True
    assert ms.stationary_confident(100.1) is False   # can't confidently say stopped


def test_failsafe_stale_assumes_moving():
    ms = MotionState(moving_mps=2.0, stale_s=3.0)
    ms.update(speed_mps=0.0, gps_available=True, now=100.0)   # stopped, but...
    assert ms.moving_for_gate(110.0) is True          # ...10s stale -> assume moving
    assert ms.stationary_confident(110.0) is False
