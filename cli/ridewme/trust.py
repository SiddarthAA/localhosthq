"""L3 — the drowsiness score, as a penalty/recovery "debt".

Baseline is 0 (wide awake). Eye closure adds penalty — the deeper and the longer
the eyes stay shut, the faster the score climbs; head-nod and yawn add smaller
penalties. A normal quick blink stays inside a deadzone and barely moves the score
(and recovers immediately). Keeping the eyes open pays the debt back down toward 0
each second. Sustained closure keeps climbing → alarm.

This is a decision-quality claim, not an accuracy one: the discipline is in *not*
punishing normal blinks and in demanding the driver actively earn the score back.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .signals import Signals
from .util import clamp, norm

EYES, HEAD_NOD, YAWN = "eyes", "head_nod", "yawn"


@dataclass
class TrustState:
    score: float                       # 0 = wide awake, climbs with drowsiness (debt)
    dangers: dict[str, float] = field(default_factory=dict)   # closure / head_nod / yawn (0..1)
    fired: list[str] = field(default_factory=list)            # which penalties are active now
    agree_count: int = 0


class TrustEngine:
    def __init__(self, tuning):
        self.t = tuning
        self.score = 0.0

    def update(self, s: Signals, baseline, dt: float) -> TrustState:
        t = self.t
        dt = clamp(dt, 0.0, 1.0)   # guard against stalls

        # No face or not calibrated yet -> no trustworthy evidence: recover toward 0.
        if not s.face_present or not baseline.ready or s.ear is None:
            self.score = max(0.0, self.score - t.recover_per_s * dt)
            return TrustState(score=round(self.score, 1))

        # closure: 0 when eyes are at their open baseline, 1 when fully shut.
        span = max(1e-3, baseline.ear_open - baseline.closed_ear_threshold)
        closure = clamp((baseline.ear_open - s.ear) / span, 0.0, 1.0)
        head_nod = norm(s.pitch_drop_deg, t.headnod_lo_deg, t.headnod_hi_deg)
        yawn = norm(s.mar_excess, t.yawn_lo, t.yawn_hi)
        dangers = {"closure": round(closure, 3), "head_nod": round(head_nod, 3), "yawn": round(yawn, 3)}

        fired: list[str] = []
        penalty = 0.0
        if closure > t.blink_deadzone:   # past a normal-blink deadzone -> penalize, scaled by depth
            over = (closure - t.blink_deadzone) / (1.0 - t.blink_deadzone)
            penalty += t.closure_penalty_per_s * over
            fired.append(EYES)
        if head_nod > t.penalty_activation:
            penalty += t.headnod_penalty_per_s * head_nod
            fired.append(HEAD_NOD)
        if yawn > t.penalty_activation:
            penalty += t.yawn_penalty_per_s * yawn
            fired.append(YAWN)

        if penalty > 0.0:
            self.score += penalty * dt
        else:
            self.score -= t.recover_per_s * dt   # eyes open, nothing firing -> pay the debt back
        self.score = clamp(self.score, 0.0, 100.0)

        return TrustState(score=round(self.score, 1), dangers=dangers,
                          fired=fired, agree_count=len(fired))
