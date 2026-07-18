"""L4 — context gating (design §4, Seam 1).

Even a real fatigue signal is suppressed unless the vehicle is actually moving.
The decision "are we moving?" comes from the shared `VehicleMotion` state produced
by the sensor worker (`MotionState.moving_for_gate`), which already applies the
fail-safe: if speed is stale or GPS is unavailable, it returns `moving = True`, so
we never suppress a real fatigue alert on missing data.
"""

from __future__ import annotations


class ContextGate:
    def __init__(self, tuning=None):
        self.t = tuning

    def evaluate(self, moving: bool) -> tuple[bool, str | None]:
        """Return (gated, reason). gated=True suppresses escalation output."""
        return (False, None) if moving else (True, "not_moving")
