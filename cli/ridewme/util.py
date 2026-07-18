"""Tiny numeric helpers shared across the decision layers."""

from __future__ import annotations

import math


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def norm(x: float, lo: float, hi: float) -> float:
    """Map x from [lo, hi] onto [0, 1], clamped. Returns 0 if lo >= hi."""
    if hi <= lo:
        return 0.0
    return clamp((x - lo) / (hi - lo))


def ema_alpha(dt: float, tau: float) -> float:
    """Exponential-moving-average / leaky-integrator coefficient for step `dt` and
    time-constant `tau`. Frame-rate independent, so duty-cycling doesn't distort it."""
    if tau <= 0:
        return 1.0
    return 1.0 - math.exp(-max(dt, 0.0) / tau)
