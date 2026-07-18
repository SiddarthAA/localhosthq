"""Crash-detection pipeline (sensor fusion) — a separate track from drowsiness,
same daemon, feeding the same signed-event stream.

Fire only when >= 2 of 3 agree: an acceleration spike (deviation from a running
baseline, so gravity/orientation is absorbed), a sudden GPS speed drop, and a
large rotation. The fusion *is* the false-positive reduction — a heuristic, not
"ML", so it holds up under scrutiny. On a hit, the fleet alert is instant but
authority dispatch is gated behind a driver-cancel countdown: we don't call 112
on a pothole.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from .events import CANCELLED, CONFIRMED, DETECTED, MINOR, MODERATE, SEVERE
from .util import ema_alpha

_G = 9.80665

ACCEL_SPIKE = "accel_spike"
SPEED_DROP = "speed_drop"
ROTATION = "rotation"


def _vec_mag(v: dict | None) -> float | None:
    if not v:
        return None
    try:
        return math.sqrt(v["x"] ** 2 + v["y"] ** 2 + v["z"] ** 2)
    except (KeyError, TypeError):
        return None


def _gyro_mag(g: dict | None) -> float | None:
    if not g:
        return None
    try:
        return math.sqrt(g["alpha"] ** 2 + g["beta"] ** 2 + g["gamma"] ** 2)
    except (KeyError, TypeError):
        return None


@dataclass
class CrashSignal:
    reasons: list[str]
    peak_g: float
    severity: str
    location: dict | None
    ts: float


class CrashFusion:
    """Consumes sensor packets, emits a CrashSignal when >=2 of 3 corroborate."""

    def __init__(self, tuning):
        self.t = tuning
        self._accel_baseline_g = 1.0     # accelG at rest ~1g; EMA absorbs it
        self._have_baseline = False
        self._speed_hist: deque[tuple[float, float]] = deque()
        self._last_active: dict[str, float] = {}
        self._peak_g = 0.0
        self._cooldown_until = 0.0
        self._last_ts: float | None = None

    def latest_speed(self, packet: dict) -> float | None:
        gps = packet.get("gps") or {}
        sp = gps.get("speed")
        return float(sp) if isinstance(sp, (int, float)) else None

    def update(self, packet: dict, ts: float) -> CrashSignal | None:
        # ── acceleration spike (deviation from running baseline) ──────────
        mag = _vec_mag(packet.get("accelG")) or _vec_mag(packet.get("accel"))
        spike_g = 0.0
        if mag is not None:
            g = mag / _G
            if not self._have_baseline:
                self._accel_baseline_g = g
                self._have_baseline = True
            spike_g = abs(g - self._accel_baseline_g)
            # Update the baseline slowly (transient crash won't move it much).
            dt = 0.02 if self._last_ts is None else max(0.0, ts - self._last_ts)
            self._accel_baseline_g += (g - self._accel_baseline_g) * ema_alpha(
                dt, self.t.accel_baseline_tau_s
            )
            self._peak_g = max(self._peak_g, g)
            if spike_g >= self.t.accel_spike_g:
                self._last_active[ACCEL_SPIKE] = ts

        # ── sudden GPS speed drop ─────────────────────────────────────────
        speed = self.latest_speed(packet)
        if speed is not None:
            self._speed_hist.append((ts, speed))
            while self._speed_hist and ts - self._speed_hist[0][0] > self.t.speed_drop_window_s:
                self._speed_hist.popleft()
            peak_speed = max((s for _, s in self._speed_hist), default=speed)
            if peak_speed - speed >= self.t.speed_drop_mps:
                self._last_active[SPEED_DROP] = ts

        # ── large rotation ────────────────────────────────────────────────
        rot = _gyro_mag(packet.get("gyro"))
        if rot is not None and rot >= self.t.rotation_dps:
            self._last_active[ROTATION] = ts

        self._last_ts = ts

        if ts < self._cooldown_until:
            return None

        # >=2 of 3 must have been active within the agreement window.
        active = [r for r, t in self._last_active.items() if ts - t <= self.t.crash_agree_window_s]
        if len(active) < 2:
            return None

        peak_g = self._peak_g
        signal = CrashSignal(
            reasons=sorted(active),
            peak_g=round(peak_g, 2),
            severity=self._severity(peak_g),
            location=self._location(packet),
            ts=ts,
        )
        # One incident per crash: cool down and reset transient trackers.
        self._cooldown_until = ts + self.t.cancel_window_s + 5.0
        self._last_active.clear()
        self._peak_g = 0.0
        return signal

    def _severity(self, peak_g: float) -> str:
        if peak_g >= self.t.severity_severe_g:
            return SEVERE
        if peak_g >= self.t.severity_moderate_g:
            return MODERATE
        return MINOR

    @staticmethod
    def _location(packet: dict) -> dict | None:
        gps = packet.get("gps") or {}
        if "lat" in gps and "lon" in gps:
            return {"lat": gps.get("lat"), "lon": gps.get("lon"), "speed_mps": gps.get("speed")}
        return None


@dataclass
class Incident:
    incident_id: str
    severity: str
    peak_g: float
    reasons: list[str]
    location: dict | None
    detected_at: float
    deadline: float
    status: str = DETECTED
    resolved_at: float | None = None


@dataclass
class IncidentUpdate:
    incident: Incident
    status: str
    cancel_window_s: float


class IncidentManager:
    """Drives the crash lifecycle: detected -> (cancel window) -> confirmed | cancelled.

    Confirmed implies authority dispatch. Returns IncidentUpdate objects for the
    daemon to turn into signed `crash` events.
    """

    def __init__(self, tuning, session_id: str):
        self.t = tuning
        self.session_id = session_id
        self.active: Incident | None = None
        self._n = 0

    def on_signal(self, sig: CrashSignal, now: float) -> IncidentUpdate | None:
        if self.active is not None and self.active.status == DETECTED:
            return None  # already handling a live incident
        self._n += 1
        inc = Incident(
            incident_id=f"crash-{self.session_id}-{self._n}",
            severity=sig.severity, peak_g=sig.peak_g, reasons=sig.reasons,
            location=sig.location, detected_at=now, deadline=now + self.t.cancel_window_s,
        )
        self.active = inc
        return IncidentUpdate(inc, DETECTED, self.t.cancel_window_s)

    def tick(self, now: float) -> IncidentUpdate | None:
        inc = self.active
        if inc is not None and inc.status == DETECTED and now >= inc.deadline:
            inc.status = CONFIRMED
            inc.resolved_at = now
            return IncidentUpdate(inc, CONFIRMED, self.t.cancel_window_s)
        return None

    def cancel(self, now: float) -> IncidentUpdate | None:
        inc = self.active
        if inc is not None and inc.status == DETECTED:
            inc.status = CANCELLED
            inc.resolved_at = now
            return IncidentUpdate(inc, CANCELLED, self.t.cancel_window_s)
        return None
