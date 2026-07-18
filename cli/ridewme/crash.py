"""The crash engine — pre-gate + three layers (design §2), running in the daemon
alongside the drowsiness engine and feeding the same signed timeline.

Funnel, progressively more certain, escalating only as far as it earns:
  pre-gate  — was the vehicle moving before? (free; kills parked jolts)
  Layer 1   — accel-spike wake-up -> a candidate (internal only, never emitted)
  Layer 2   — score a ~2s window: peak accel + jerk, gyro >=2 axes, GPS speed-drop;
              >=2 agree -> `crash.unconfirmed` (fleet only), start the human window
  Layer 3   — severity-modulated window + post-event motion (de-escalation) + driver
              cancel -> terminal `confirmed` (emergency services) / `cancelled`

Invariants: emergency services only ever hear `confirmed`; no trained model on the
path — the fusion heuristic is the intelligence. Orientation-agnostic (magnitude +
deviation-from-baseline); GPS is optional and never required for a decision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import events as E
from .ringbuffer import Sample, SampleRing
from .util import clamp, ema_alpha

_G = 9.80665

ACCEL_JERK = "accel_jerk"
GYRO = "gyro"
SPEED_DROP = "speed_drop"


def _mag(v: dict | None) -> float | None:
    if not v:
        return None
    try:
        return math.sqrt(v["x"] ** 2 + v["y"] ** 2 + v["z"] ** 2)
    except (KeyError, TypeError):
        return None


def _gyro_axes(g: dict | None) -> tuple[float, float, float]:
    if not g:
        return (0.0, 0.0, 0.0)
    try:
        return (abs(float(g["alpha"])), abs(float(g["beta"])), abs(float(g["gamma"])))
    except (KeyError, TypeError, ValueError):
        return (0.0, 0.0, 0.0)


@dataclass
class Corroboration:
    confirmed: bool
    severity: str
    peak_g: float
    jerk: float
    signals_fired: list[str]
    location: dict | None


@dataclass
class Incident:
    incident_id: str
    severity: str
    peak_g: float
    jerk: float
    signals_fired: list[str]
    location: dict | None
    detected_at: float
    window_s: float
    deadline: float
    fatigue_context: dict | None
    status: str = E.UNCONFIRMED


@dataclass
class _PendingL2:
    ts: float


class CrashEngine:
    """Owns the ring buffer + accel baseline; drives the crash funnel; emits crash
    events via `emit_fn(payload, ts)` and drives an optional `alarm_fn(active, intensity)`.
    `fatigue_fn(now)` supplies the correlation block (design §5)."""

    def __init__(self, tuning, motion, session_id, emit_fn, fatigue_fn=None, alarm_fn=None):
        self.t = tuning
        self.motion = motion
        self.session_id = session_id
        self._emit = emit_fn
        self._fatigue_fn = fatigue_fn or (lambda now: None)
        self._alarm = alarm_fn or (lambda active, intensity: None)

        self.ring = SampleRing(tuning.sensor_ring_s)
        self._baseline_g = 1.0
        self._have_baseline = False
        self._last_ts: float | None = None
        self._last_location: dict | None = None

        self._pending: _PendingL2 | None = None
        self._incident: Incident | None = None
        self._cooldown_until = 0.0
        self._deesc_since: float | None = None
        self._n = 0

    @property
    def active_incident(self) -> Incident | None:
        return self._incident

    # ── ingest one sensor sample (design §3) ──────────────────────────
    def ingest(self, packet: dict, ts: float) -> None:
        mag = _mag(packet.get("accelG")) or _mag(packet.get("accel"))
        gx, gy, gz = _gyro_axes(packet.get("gyro"))
        gyro_mag = math.sqrt(gx * gx + gy * gy + gz * gz)

        gps = packet.get("gps") or {}
        speed = gps.get("speed") if isinstance(gps.get("speed"), (int, float)) else None
        gps_available = "lat" in gps and "lon" in gps
        if gps_available:
            self._last_location = {"lat": gps.get("lat"), "lon": gps.get("lon"), "speed_mps": speed}

        accel_g = (mag / _G) if mag is not None else self._baseline_g
        if not self._have_baseline:
            self._baseline_g = accel_g
            self._have_baseline = True
        dt = 0.02 if self._last_ts is None else max(0.0, ts - self._last_ts)
        dev = abs(accel_g - self._baseline_g)
        # Update the slow baseline (a transient impact barely moves it).
        self._baseline_g += (accel_g - self._baseline_g) * ema_alpha(dt, self.t.accel_baseline_tau_s)
        self._last_ts = ts

        self.ring.add(Sample(ts=ts, accel_g=accel_g, accel_dev_g=dev,
                             gyro=(gx, gy, gz), gyro_mag=gyro_mag,
                             speed_mps=speed, gps_available=gps_available))
        self.motion.update(speed, gps_available, ts)

        # Layer 1 — trigger. Only when idle (no candidate, no incident, not cooling down).
        if self._incident is None and self._pending is None and ts >= self._cooldown_until:
            if dev >= self.t.accel_spike_g and self._pre_gate_ok(ts):
                self._pending = _PendingL2(ts)   # collect the post-window, then corroborate

    # ── pre-gate (design §2) ──────────────────────────────────────────
    def _pre_gate_ok(self, ts: float) -> bool:
        pre = [s for s in self.ring.window(ts, before=2.0, after=0.0) if s.ts <= ts - 0.3]
        gps_pre = [s for s in pre if s.gps_available and s.speed_mps is not None]
        if not gps_pre:
            return True   # no GPS -> fail open into Layer 2 (better to over-evaluate than miss)
        return max(s.speed_mps for s in gps_pre) >= self.t.pregate_min_speed_mps

    # ── periodic tick: Layer 2 eval + Layer 3 countdown ───────────────
    def tick(self, now: float) -> None:
        if self._pending is not None and now >= self._pending.ts + self.t.crash_l2_window_s:
            t0 = self._pending.ts
            self._pending = None
            result = self._corroborate(t0)
            if result.confirmed:
                self._start_layer3(result, now)
            else:
                self._cooldown_until = now + self.t.crash_cooldown_s  # rejected candidate

        if self._incident is not None:
            self._run_layer3(now)

    # ── Layer 2 — corroboration (design §2) ───────────────────────────
    def _corroborate(self, t0: float) -> Corroboration:
        win = self.ring.window(t0, before=0.5, after=self.t.crash_l2_window_s)
        if not win:
            return Corroboration(False, E.MINOR, 0.0, 0.0, [], self._last_location)

        peak = max(s.accel_dev_g for s in win)
        jerk = 0.0
        for a, b in zip(win, win[1:]):
            dt = max(1e-3, b.ts - a.ts)
            jerk = max(jerk, abs(b.accel_dev_g - a.accel_dev_g) / dt)

        axes_hot = sum(
            1 for axis in range(3)
            if max(s.gyro[axis] for s in win) >= self.t.gyro_axis_dps
        )

        gps_win = [s for s in win if s.gps_available and s.speed_mps is not None]
        speed_drop = False
        if gps_win:
            speeds = [s.speed_mps for s in gps_win]
            speed_drop = (max(speeds) - min(speeds) >= self.t.speed_drop_mps
                          and min(speeds) <= self.t.speed_drop_end_mps)

        fired: list[str] = []
        if peak >= self.t.accel_spike_g and jerk >= self.t.jerk_g_per_s:
            fired.append(ACCEL_JERK)
        if axes_hot >= self.t.gyro_axes_required:
            fired.append(GYRO)
        if speed_drop:
            fired.append(SPEED_DROP)

        return Corroboration(
            confirmed=len(fired) >= 2,
            severity=self._severity(peak),
            peak_g=round(peak, 2), jerk=round(jerk, 1),
            signals_fired=fired, location=self._last_location,
        )

    def _severity(self, peak_g: float) -> str:
        if peak_g >= self.t.severity_severe_g:
            return E.SEVERE
        if peak_g >= self.t.severity_moderate_g:
            return E.MODERATE
        return E.MINOR

    # ── Layer 3 — behavioral confirmation (design §2) ─────────────────
    def _start_layer3(self, r: Corroboration, now: float) -> None:
        self._n += 1
        window = (self.t.crash_l3_window_severe_s if r.severity == E.SEVERE
                  else self.t.crash_l3_window_s)
        inc = Incident(
            incident_id=f"crash-{self.session_id}-{self._n}",
            severity=r.severity, peak_g=r.peak_g, jerk=r.jerk, signals_fired=r.signals_fired,
            location=r.location, detected_at=now, window_s=window, deadline=now + window,
            fatigue_context=self._fatigue_fn(now),
        )
        self._incident = inc
        self._deesc_since = None
        self._emit_incident(inc, now)   # crash.unconfirmed -> fleet only

    def _run_layer3(self, now: float) -> None:
        inc = self._incident
        assert inc is not None

        # Post-event motion (weighted de-escalation): sustained normal driving cancels.
        m = self.motion.get()
        moving_fast = m.gps_available and m.speed_mps is not None and m.speed_mps >= self.t.deescalate_speed_mps
        if moving_fast:
            if self._deesc_since is None:
                self._deesc_since = now
            elif now - self._deesc_since >= self.t.deescalate_sustained_s:
                self._resolve(E.CANCELLED, now, reason=E.REASON_DEESCALATED)
                return
        else:
            self._deesc_since = None

        if now >= inc.deadline:
            final_motion = "stopped" if self.motion.stationary_confident(now) else "moving"
            self._resolve(E.CONFIRMED, now, final_motion=final_motion)
            return

        intensity = clamp((now - inc.detected_at) / max(1e-3, inc.window_s))
        self._alarm(True, intensity)   # escalating in-cabin alarm during the window

    # ── driver cancel + demo inject ───────────────────────────────────
    def cancel(self, now: float) -> bool:
        """Physical button / voice (design §2) — the safe cancel input."""
        if self._incident is not None and self._incident.status == E.UNCONFIRMED:
            self._resolve(E.CANCELLED, now, reason=E.REASON_DRIVER)
            return True
        return False

    def simulate_impact(self, now: float, severity: str = E.SEVERE) -> None:
        """Demo inject (design §10, §13): force a fully-corroborated candidate now."""
        if self._incident is not None or now < self._cooldown_until:
            return
        peak = self.t.severity_severe_g + 1.0 if severity == E.SEVERE else self.t.severity_moderate_g + 0.5
        r = Corroboration(True, severity, round(peak, 2), 90.0,
                          [ACCEL_JERK, GYRO, SPEED_DROP], self._last_location)
        self._start_layer3(r, now)

    # ── terminal + emission ───────────────────────────────────────────
    def _resolve(self, status: str, now: float, reason: str | None = None,
                 final_motion: str | None = None) -> None:
        inc = self._incident
        assert inc is not None
        inc.status = status
        self._alarm(False, 0.0)
        self._emit_incident(inc, now, reason=reason, final_motion=final_motion)
        self._incident = None
        self._deesc_since = None
        self._cooldown_until = now + self.t.crash_cooldown_s

    def _emit_incident(self, inc: Incident, ts: float,
                       reason: str | None = None, final_motion: str | None = None) -> None:
        payload = {
            "incident_id": inc.incident_id,
            "status": inc.status,
            "severity": inc.severity,
            "peak_g": inc.peak_g,
            "jerk": inc.jerk,
            "signals_fired": inc.signals_fired,
            "location": inc.location,
            "window_seconds": round(inc.window_s, 1),
            "cancel_window_s": round(inc.window_s, 1),   # frontend cosmetic countdown
            "fatigue_context": inc.fatigue_context,
            "ts_detected": round(inc.detected_at, 3),
        }
        if reason is not None:
            payload["reason"] = reason
        if final_motion is not None:
            payload["final_motion"] = final_motion
        self._emit(payload, ts)
