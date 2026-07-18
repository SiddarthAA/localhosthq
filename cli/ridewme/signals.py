"""L1 — Multi-signal extraction.

From per-frame face geometry, derive *independent* fatigue measurements over time:
PERCLOS (the clinical backbone), blink rate + duration (slow long blinks are the
real tell), head-nod (pitch drop), yawn (mouth-aspect). These are measurements
only — turning them into danger + a decision is L3's job (trust.py). Principle:
never trust one cue.

Everything here is pure and time-driven, so it unit-tests without a camera: feed
synthetic `RawFeatures` and timestamps.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class RawFeatures:
    """Per-frame geometry out of L0 perception (or synthesized in tests)."""

    face_present: bool
    ear: float          # eye-aspect ratio, avg of both eyes (~0.3 open, ~0.1 closed)
    mar: float          # mouth-aspect ratio (higher = mouth open)
    pitch_deg: float    # head pitch in degrees; lower = looking/nodding down
    eyeblink: float = 0.0  # optional blendshape corroboration, 0..1 (0 = unknown)
    jawopen: float = 0.0   # optional blendshape, 0..1


@dataclass
class Signals:
    """Time-aware fatigue measurements. Consumed by the trust engine."""

    face_present: bool
    ear: float | None
    eye_closed: bool
    perclos: float          # 0..1, fraction of the window with eyes closed
    blink_rate: float       # blinks per minute
    blink_dur_ms: float     # representative recent blink duration
    pitch_drop_deg: float   # >= 0, head-down deviation from neutral
    mar_excess: float       # mouth-aspect over the driver's neutral


class SignalExtractor:
    """Rolling-window extractor. `baseline` supplies the per-driver closed-eye
    threshold and neutral pose (L2); pass a not-ready baseline before calibration
    and the extractor falls back to conservative global constants."""

    _FALLBACK_CLOSED_EAR = 0.18
    _MIN_BLINK_MS = 50.0
    _MAX_BLINK_MS = 800.0

    def __init__(self, tuning):
        self.t = tuning
        self._closed_hist: deque[tuple[float, bool]] = deque()   # (ts, closed)
        self._blinks: deque[tuple[float, float]] = deque()       # (end_ts, duration_ms)
        self._eye_closed = False
        self._closed_since: float | None = None
        self._blink_dur_ema = tuning.base_blink_ms

    def update(self, raw: RawFeatures, ts: float, baseline) -> Signals:
        if not raw.face_present or raw.ear is None:
            # No face — hold windows but report nothing new; trust decays on this.
            return Signals(
                face_present=False, ear=None, eye_closed=False,
                perclos=self._perclos(ts), blink_rate=self._blink_rate(ts),
                blink_dur_ms=self._blink_dur_ema, pitch_drop_deg=0.0, mar_excess=0.0,
            )

        closed_thresh = (
            baseline.closed_ear_threshold if baseline.ready else self._FALLBACK_CLOSED_EAR
        )
        eye_closed = raw.ear < closed_thresh

        # PERCLOS window (time-weighted so duty-cycling doesn't bias it).
        self._closed_hist.append((ts, eye_closed))
        self._evict(self._closed_hist, ts, self.t.perclos_window_s)

        # Blink state machine: open->closed starts a blink, closed->open ends one.
        if eye_closed and not self._eye_closed:
            self._closed_since = ts
        elif not eye_closed and self._eye_closed and self._closed_since is not None:
            dur_ms = (ts - self._closed_since) * 1000.0
            if self._MIN_BLINK_MS <= dur_ms <= self._MAX_BLINK_MS:
                self._blinks.append((ts, dur_ms))
                # EMA of recent blink durations — the "slow blink" tell.
                self._blink_dur_ema += 0.4 * (dur_ms - self._blink_dur_ema)
            self._closed_since = None
        self._eye_closed = eye_closed
        self._evict(self._blinks, ts, self.t.blink_window_s)

        pitch_drop = max(0.0, (baseline.pitch_neutral - raw.pitch_deg)) if baseline.ready else 0.0
        mar_excess = max(0.0, raw.mar - baseline.mar_neutral) if baseline.ready else 0.0

        return Signals(
            face_present=True,
            ear=raw.ear,
            eye_closed=eye_closed,
            perclos=self._perclos(ts),
            blink_rate=self._blink_rate(ts),
            blink_dur_ms=self._blink_dur_ema,
            pitch_drop_deg=pitch_drop,
            mar_excess=mar_excess,
        )

    # ── windows ───────────────────────────────────────────────────────
    @staticmethod
    def _evict(dq: deque, now: float, window: float) -> None:
        while dq and now - dq[0][0] > window:
            dq.popleft()

    def _perclos(self, now: float) -> float:
        """Time-weighted fraction of the window with eyes closed."""
        if len(self._closed_hist) < 2:
            return 0.0
        closed_time = 0.0
        total = 0.0
        items = list(self._closed_hist)
        for (t0, c0), (t1, _) in zip(items, items[1:]):
            dt = t1 - t0
            total += dt
            if c0:
                closed_time += dt
        return closed_time / total if total > 0 else 0.0

    def _blink_rate(self, now: float) -> float:
        if not self._blinks:
            return 0.0
        span_min = self.t.blink_window_s / 60.0
        return len(self._blinks) / span_min if span_min > 0 else 0.0
