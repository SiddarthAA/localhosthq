"""L3 — Corroboration + persistence. THE MOAT.

A fatigue *score* rises only when multiple independent signals AGREE and the
condition PERSISTS over seconds — a leaky integrator, not an instant threshold
trip. PERCLOS is the backbone, but a *single* signal is capped at a whisper;
only agreement unlocks a real alarm. This is the false-positive killer, and it's
a decision-quality claim, not an accuracy one — so no dataset "beats" it.

Do NOT flatten this into a plain threshold. The continuous, corroborated,
time-integrated `score` IS the product.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .signals import Signals
from .util import clamp, ema_alpha, norm

# The corroboration channels. PERCLOS is the backbone; the rest are independent tells.
CHANNELS = ("perclos", "blink", "head_nod", "yawn")


@dataclass
class TrustState:
    score: float                       # 0..100, corroborated + persistent
    dangers: dict[str, float] = field(default_factory=dict)   # per-channel 0..1
    fired: list[str] = field(default_factory=list)            # channels above activation
    agree_count: int = 0


class TrustEngine:
    def __init__(self, tuning):
        self.t = tuning
        self.score = 0.0

    def _dangers(self, s: Signals) -> dict[str, float]:
        t = self.t
        return {
            "perclos": norm(s.perclos, t.perclos_lo, t.perclos_hi),
            "blink": norm(s.blink_dur_ms, t.base_blink_ms, t.long_blink_ms),
            "head_nod": norm(s.pitch_drop_deg, t.headnod_lo_deg, t.headnod_hi_deg),
            "yawn": norm(s.mar_excess, t.yawn_lo, t.yawn_hi),
        }

    def update(self, s: Signals, baseline, dt: float) -> TrustState:
        dt = clamp(dt, 0.0, 1.0)  # guard against stalls distorting the integrator

        # No face or no baseline yet => no trustworthy evidence; decay toward calm.
        if not s.face_present or not baseline.ready:
            self.score += (0.0 - self.score) * ema_alpha(dt, self.t.fall_tau_s)
            return TrustState(score=self.score)

        dangers = self._dangers(s)
        fired = [c for c, d in dangers.items() if d > self.t.activation]
        agree = len(fired)

        weights = self.t.weights
        raw = sum(weights[c] * dangers[c] for c in CHANNELS)  # weights sum to 1 -> 0..1

        # ── Corroboration gate: a lone signal is only a whisper. ──────────
        if agree <= 1:
            lone_is_perclos = agree == 1 and fired[0] == "perclos"
            cap = self.t.single_cap_perclos if lone_is_perclos else self.t.single_cap_other
            target = min(raw, cap)
        elif agree == 2:
            target = min(raw, self.t.pair_cap)
        else:  # >= 3 agree -> full range unlocked, a real alarm is possible
            target = raw

        # Backbone override: sustained eye-closure (microsleep) is dangerous on its
        # own, but even then it's capped below full alarm unless corroborated.
        if dangers["perclos"] >= self.t.perclos_override:
            target = max(target, self.t.perclos_override_target)

        target100 = target * 100.0

        # ── Persistence: leaky integrator, rises slowly, backs off slower. ─
        tau = self.t.rise_tau_s if target100 > self.score else self.t.fall_tau_s
        self.score += (target100 - self.score) * ema_alpha(dt, tau)
        self.score = clamp(self.score, 0.0, 100.0)

        return TrustState(score=self.score, dangers=dangers, fired=fired, agree_count=agree)
