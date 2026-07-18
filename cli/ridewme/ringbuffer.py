"""Sample ring buffer for the crash engine (design §3).

Crashes peak in <100 ms, so we must retain *every* source-timestamped sample
around an event — not just the freshest. This rolling ~3–5 s buffer is what lets
Layer 2 score the full pre-and-post window the instant a candidate fires.

Orientation-agnostic by construction: each Sample carries acceleration as a
magnitude *deviation from a slow baseline* (gravity + mounting washed out), plus
per-axis gyro. Pure/time-driven, so it unit-tests without any hardware.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class Sample:
    ts: float                       # source timestamp (seconds)
    accel_g: float                  # |accelG| / g  (raw magnitude, ~1.0 at rest)
    accel_dev_g: float              # deviation from the slow baseline (orientation/gravity washed out)
    gyro: tuple[float, float, float]  # per-axis rotation rate (deg/s)
    gyro_mag: float                 # |gyro|
    speed_mps: float | None         # GPS speed, or None if unavailable
    gps_available: bool


class SampleRing:
    def __init__(self, window_s: float):
        self.window_s = window_s
        self._dq: deque[Sample] = deque()

    def add(self, s: Sample) -> None:
        self._dq.append(s)
        cutoff = s.ts - self.window_s        # evict relative to the newest sample's clock
        while self._dq and self._dq[0].ts < cutoff:
            self._dq.popleft()

    def window(self, t0: float, before: float, after: float) -> list[Sample]:
        lo, hi = t0 - before, t0 + after
        return [s for s in self._dq if lo <= s.ts <= hi]

    def since(self, t0: float) -> list[Sample]:
        return [s for s in self._dq if s.ts >= t0]

    def latest(self) -> Sample | None:
        return self._dq[-1] if self._dq else None

    def __len__(self) -> int:
        return len(self._dq)
