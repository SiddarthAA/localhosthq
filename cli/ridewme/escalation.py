"""L5 — Graduated escalation with hysteresis.

The score maps to a tiered, proportionate response: quiet note -> soft chime ->
loud alarm that intensifies with duration and backs off on recovery. Hysteresis
(separate up/down thresholds) keeps it from flapping around a boundary. Not a
binary klaxon drivers learn to hate.

The L4 gate can suppress the *output* (audio) while the underlying decision is
still reported — so the dashboard shows "monitoring (parked)", not an alarm.
"""

from __future__ import annotations

from dataclasses import dataclass

from .events import ALARM, AWAKE, LEVEL_RANK, LEVELS, NOTICE, WARN
from .util import clamp


@dataclass
class Escalation:
    level: str              # the raw decision level (reported to the fleet)
    prev_level: str
    transition: bool
    effective_level: str    # after the L4 gate (drives audio); == level unless gated
    gated: bool
    audio_intensity: float  # 0..1, ramps while sustained in alarm


class Escalator:
    def __init__(self, tuning):
        self.t = tuning
        self.level = AWAKE
        self.time_in_level = 0.0

    def _rise_target(self, score: float) -> str:
        if score >= self.t.up_alarm:
            return ALARM
        if score >= self.t.up_warn:
            return WARN
        if score >= self.t.up_notice:
            return NOTICE
        return AWAKE

    def _fall_floor(self, score: float) -> str:
        # The lowest level allowed at this score given the (lower) down-thresholds.
        if score >= self.t.down_alarm:
            return ALARM
        if score >= self.t.down_warn:
            return WARN
        if score >= self.t.down_notice:
            return NOTICE
        return AWAKE

    def update(self, score: float, dt: float, gated: bool) -> Escalation:
        cur = LEVEL_RANK[self.level]
        up = LEVEL_RANK[self._rise_target(score)]
        down = LEVEL_RANK[self._fall_floor(score)]

        if cur < up:            # crossed an up-threshold -> rise
            new_rank = up
        elif cur > down:        # fell below a down-threshold -> fall
            new_rank = down
        else:                   # inside the hysteresis band -> hold
            new_rank = cur

        new_level = LEVELS[new_rank]
        transition = new_level != self.level
        prev = self.level
        if transition:
            self.level = new_level
            self.time_in_level = 0.0
        else:
            self.time_in_level += dt

        effective = AWAKE if gated else self.level
        intensity = (
            clamp(self.time_in_level / self.t.alarm_intensify_s)
            if effective == ALARM else 0.0
        )
        return Escalation(
            level=self.level, prev_level=prev, transition=transition,
            effective_level=effective, gated=gated, audio_intensity=intensity,
        )
