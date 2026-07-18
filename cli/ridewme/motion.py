"""Shared vehicle-motion state — Seam 1 (design §4).

The sensor worker is the *single producer*: it computes motion from GPS and writes
this small thread-safe object. The camera/drowsiness worker is the *consumer*: it
reads `moving_for_gate()` each tick for its L4 context gate.

Fail-safe rule (critical): if the motion state is stale or GPS is unavailable, the
drowsiness gate assumes **moving = true** so it never suppresses a real fatigue
alert. This replaces Feature 1's hardcoded vehicle-moving flag.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class VehicleMotion:
    moving: bool
    speed_mps: float | None
    gps_available: bool
    updated_ts: float


class MotionState:
    def __init__(self, moving_mps: float, stale_s: float = 3.0):
        self._moving_mps = moving_mps
        self._stale_s = stale_s
        self._lock = threading.Lock()
        self._m = VehicleMotion(moving=False, speed_mps=None, gps_available=False, updated_ts=0.0)

    def update(self, speed_mps: float | None, gps_available: bool, now: float) -> None:
        moving = gps_available and speed_mps is not None and speed_mps >= self._moving_mps
        with self._lock:
            self._m = VehicleMotion(moving, speed_mps, gps_available, now)

    def get(self) -> VehicleMotion:
        with self._lock:
            return self._m

    def moving_for_gate(self, now: float) -> bool:
        """Fail-safe: assume moving unless a FRESH GPS fix says we're stopped."""
        m = self.get()
        if not m.gps_available or (now - m.updated_ts) > self._stale_s:
            return True
        return m.moving

    def stationary_confident(self, now: float) -> bool:
        """True only when a fresh GPS fix confidently says stopped (crash pre-gate)."""
        m = self.get()
        return (
            m.gps_available
            and (now - m.updated_ts) <= self._stale_s
            and m.speed_mps is not None
            and m.speed_mps < self._moving_mps
        )
