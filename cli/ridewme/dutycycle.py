"""L6 — Adaptive duty-cycling. The efficiency flex.

When the driver is clearly alert — score near zero, no signals firing — drop
inference to a few fps. The moment anything stirs, ramp back to full rate
instantly. Drowsiness moves over seconds, so you lose nothing but slash compute,
power and heat on a fanless board. "When not to compute" — the sibling of "when
not to alert."
"""

from __future__ import annotations

from dataclasses import dataclass

FULL = "full"
IDLE = "idle"


@dataclass
class Duty:
    target_fps: int
    state: str  # "full" | "idle"


class DutyCycler:
    def __init__(self, tuning):
        self.t = tuning
        self._quiet_since: float | None = None
        self.state = FULL

    def update(self, score: float, agree_count: int, now: float) -> Duty:
        quiet = score < self.t.idle_score and agree_count == 0
        if quiet:
            if self._quiet_since is None:
                self._quiet_since = now
            if now - self._quiet_since >= self.t.idle_grace_s:
                self.state = IDLE
                return Duty(self.t.fps_idle, IDLE)
            return Duty(self.t.fps_full, self.state)
        # Anything stirs -> instant ramp back to full.
        self._quiet_since = None
        self.state = FULL
        return Duty(self.t.fps_full, FULL)
