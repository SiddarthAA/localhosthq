"""L4 — Context gating.

Even a real fatigue signal is suppressed unless context says it matters: the
vehicle has to actually be moving (GPS speed, from the fusion side). Don't nag a
parked driver. This is the seam where the camera pipeline and the sensor pipeline
fuse into one system.

Fail-open: if speed is unknown (no GPS fix), we do NOT gate — better to alert
than to silently miss real drowsiness because a fix was missing.
"""

from __future__ import annotations


class ContextGate:
    def __init__(self, tuning):
        self.t = tuning

    def evaluate(self, speed_mps: float | None) -> tuple[bool, str | None]:
        """Return (gated, reason). gated=True suppresses escalation output."""
        if speed_mps is None:
            return (False, None)
        if speed_mps < self.t.moving_mps:
            return (True, "not_moving")
        return (False, None)
