"""Fatigue correlation history (design §5) — the "1 + 1 = 3" payoff.

The drowsiness engine writes its score here each tick; the crash engine reads a
`fatigue_context` block when an incident fires. A crash that follows a rising
fatigue score is almost certainly a fatigue-caused crash — a signed correlation no
standalone crash sensor or camera could produce. Thread-safe: camera writes,
crash reads.
"""

from __future__ import annotations

import threading
from collections import deque


class FatigueHistory:
    def __init__(self, window_min: float, elevated_score: float):
        self._window_s = window_min * 60.0
        self._elevated = elevated_score
        self._dq: deque[tuple[float, float]] = deque()   # (ts, score)
        self._lock = threading.Lock()

    def update(self, ts: float, score: float) -> None:
        with self._lock:
            self._dq.append((ts, score))
            cutoff = ts - self._window_s
            while self._dq and self._dq[0][0] < cutoff:
                self._dq.popleft()

    def context(self, now: float) -> dict:
        with self._lock:
            items = [x for x in self._dq if x[0] >= now - self._window_s]
        if not items:
            return {"recent_max_score": 0.0, "was_elevated": False,
                    "elevated_seconds": 0.0, "sampled_over_minutes": 0.0}
        max_score = max(s for _, s in items)
        elevated_s = 0.0
        for (t0, s0), (t1, _) in zip(items, items[1:]):
            if s0 >= self._elevated:
                elevated_s += t1 - t0
        span = items[-1][0] - items[0][0]
        return {
            "recent_max_score": round(max_score, 1),
            "was_elevated": elevated_s > 0 or max_score >= self._elevated,
            "elevated_seconds": round(elevated_s, 1),
            "sampled_over_minutes": round(min(self._window_s, span) / 60.0, 1),
        }
