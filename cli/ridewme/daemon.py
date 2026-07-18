"""Orchestration — how it all talks, inside the daemon.

Two parallel reader-driven loops, each non-blocking:
  * camera loop  — L0 -> L5 (+ L6 controlling its own rate), emits drowsiness events.
  * sensor loop  — crash fusion + incident lifecycle, emits crash events.
Plus a heartbeat loop (liveness + duty telemetry). GPS speed crosses from the
sensor loop into the camera loop's L4 context gate. Every layer's decision funnels
through one signed-event chain and one outbound uplink.
"""

from __future__ import annotations

import threading
import time
import uuid

from . import events as E
from .audio import AudioEngine
from .calibration import BaselineCalibrator
from .config import Config
from .dutycycle import DutyCycler
from .escalation import Escalator
from .fusion import CrashFusion, IncidentManager
from .gating import ContextGate
from .naive import NaiveDetector
from .outbox import Outbox
from .signals import SignalExtractor
from .signing import EventChain, load_or_create_key
from .trust import TrustEngine
from .uplink import Uplink


def _r(x, n=3):
    return round(float(x), n)


class Daemon:
    def __init__(self, cfg: Config, feature_source, sensor_source):
        self.cfg = cfg
        self.t = cfg.tuning
        self.session_id = "s-" + uuid.uuid4().hex[:10]

        key = load_or_create_key(cfg.key_path)
        self.chain = EventChain(key, cfg.driver_id, self.session_id)
        self.outbox = Outbox(cfg.outbox_path)     # durable store-and-forward on the edge
        self.uplink = Uplink(cfg, self.outbox)

        self.fsrc = feature_source
        self.ssrc = sensor_source

        self.extractor = SignalExtractor(self.t)
        self.calib = BaselineCalibrator(self.t)
        self.trust = TrustEngine(self.t)
        self.gate = ContextGate(self.t)
        self.esc = Escalator(self.t)
        self.audio = AudioEngine(cfg.audio_enabled)
        self.duty = DutyCycler(self.t)
        self.fusion = CrashFusion(self.t)
        self.incidents = IncidentManager(self.t, self.session_id)
        self.naive = NaiveDetector() if cfg.naive_mode else None

        self._speed: float | None = None
        self._speed_lock = threading.Lock()
        self._emit_lock = threading.Lock()   # serialize chain.make across threads
        self._stop = threading.Event()

        self._start_t = time.time()
        self._fps = 0.0
        self._duty_state = "full"
        self._camera_ok = False
        self._last_sample_t = 0.0
        self._naive_last = E.AWAKE

    # ── shared state ──────────────────────────────────────────────────
    def _set_speed(self, v):
        with self._speed_lock:
            self._speed = v

    def _get_speed(self):
        with self._speed_lock:
            return self._speed

    def _emit(self, type_: str, payload: dict, ts=None) -> dict:
        # Persist to the durable outbox under the same lock that advances the chain,
        # so on-disk order matches seq order. The uplink drains it independently.
        with self._emit_lock:
            ev = self.chain.make(type_, payload, ts)
            self.outbox.put(ev["session_id"], ev["seq"], E.to_wire(ev))
        return ev

    # ── lifecycle ─────────────────────────────────────────────────────
    def run(self) -> None:
        hello_payload = {
            "pubkey": self.chain.pubkey_b64,
            "device": self.cfg.driver_id,
            "started_at": _r(self._start_t),
            "schema": E.SCHEMA_VERSION,
            "naive": self.naive is not None,
        }
        with self._emit_lock:
            hello = self.chain.make(E.HELLO, hello_payload)
            self.outbox.put(hello["session_id"], hello["seq"], E.to_wire(hello))
        self.uplink.start(hello)   # (re)registers the session's pubkey on every connect

        print(f"[daemon] session={self.session_id} driver={self.cfg.driver_id} "
              f"uplink={self.cfg.ingest_ws_url} naive={self.naive is not None}")

        threads = [
            threading.Thread(target=self._camera_loop, name="camera", daemon=True),
            threading.Thread(target=self._sensor_loop, name="sensor", daemon=True),
            threading.Thread(target=self._heartbeat_loop, name="heartbeat", daemon=True),
        ]
        for th in threads:
            th.start()
        try:
            while not self._stop.is_set():
                self._stop.wait(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def cancel_crash(self) -> None:
        upd = self.incidents.cancel(time.time())
        if upd:
            self._emit_crash(upd, time.time())
            print("[crash] cancelled by driver.")

    def shutdown(self) -> None:
        self._stop.set()
        self.audio.stop()
        try:
            self.fsrc.close()
        except Exception:
            pass
        try:
            self.ssrc.close()
        except Exception:
            pass
        self.uplink.close()
        try:
            self.outbox.close()
        except Exception:
            pass
        print("[daemon] stopped.")

    # ── camera loop: L0 -> L5 (+ L6) ──────────────────────────────────
    def _camera_loop(self) -> None:
        last = time.time()
        target_fps = self.t.fps_full
        while not self._stop.is_set():
            loop_start = time.time()
            ok, raw, ts = self.fsrc.read()
            self._camera_ok = ok
            if not ok or raw is None:
                time.sleep(0.05)
                continue
            dt = max(1e-3, ts - last)
            last = ts
            self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt) if self._fps else 1.0 / dt

            if self.naive is not None:
                self._emit_naive(self.naive.update(raw), raw, ts)
                self._pace(loop_start, self.t.fps_full)
                continue

            baseline = self.calib.update(raw, ts)          # L2
            sig = self.extractor.update(raw, ts, baseline)  # L1
            trust = self.trust.update(sig, baseline, dt)    # L3
            gated, reason = self.gate.evaluate(self._get_speed())  # L4
            esc = self.esc.update(trust.score, dt, gated)   # L5
            self.audio.on_escalation(esc.effective_level, esc.audio_intensity)
            duty = self.duty.update(trust.score, trust.agree_count, ts)  # L6
            target_fps = duty.target_fps
            self._duty_state = duty.state

            self._maybe_emit_drowsiness(esc, trust, sig, baseline, gated, reason, ts)
            self._pace(loop_start, target_fps)

    def _pace(self, loop_start: float, fps: int) -> None:
        budget = 1.0 / max(1, fps)
        rest = budget - (time.time() - loop_start)
        if rest > 0:
            self._stop.wait(rest)

    def _maybe_emit_drowsiness(self, esc, trust, sig, baseline, gated, reason, ts) -> None:
        signals = {
            "ear": _r(sig.ear) if sig.ear is not None else None,
            "perclos": _r(sig.perclos),
            "blink_rate": _r(sig.blink_rate, 1),
            "blink_dur_ms": _r(sig.blink_dur_ms, 0),
            "head_nod": _r(trust.dangers.get("head_nod", 0.0)),
            "yawn": _r(trust.dangers.get("yawn", 0.0)),
        }
        payload = {
            "level": esc.level,
            "prev_level": esc.prev_level,
            "score": _r(trust.score, 1),
            "signals": signals,
            "fired": trust.fired,
            "agree_count": trust.agree_count,
            "gated": gated,
            "gate_reason": reason,
            "calibrated": baseline.ready,
        }
        if esc.transition:
            payload["kind"] = "transition"
            self._emit(E.DROWSINESS, payload, ts)
            print(f"[drowsy] {esc.prev_level} -> {esc.level}  score={payload['score']} "
                  f"fired={trust.fired} gated={gated}")
        elif (esc.level != E.AWAKE or trust.score > 0) and \
                ts - self._last_sample_t >= 1.0 / self.t.sample_hz:
            self._last_sample_t = ts
            payload["kind"] = "sample"
            self._emit(E.DROWSINESS, payload, ts)

    def _emit_naive(self, level: str, raw, ts) -> None:
        if level == self._naive_last:
            return
        prev = self._naive_last
        self._naive_last = level
        payload = {
            "kind": "transition", "level": level, "prev_level": prev,
            "score": 100.0 if level == E.ALARM else 0.0,
            "signals": {"ear": _r(raw.ear) if raw.ear is not None else None},
            "fired": ["naive"] if level == E.ALARM else [], "agree_count": 1,
            "gated": False, "gate_reason": None, "calibrated": False,
        }
        self._emit(E.DROWSINESS, payload, ts)

    # ── sensor loop: crash fusion + incident lifecycle ────────────────
    def _sensor_loop(self) -> None:
        while not self._stop.is_set():
            now = time.time()
            packet = self.ssrc.latest()
            if packet:
                sp = self.fusion.latest_speed(packet)
                if sp is not None:
                    self._set_speed(sp)
                sig = self.fusion.update(packet, now)
                if sig:
                    upd = self.incidents.on_signal(sig, now)
                    if upd:
                        self._emit_crash(upd, now)
            upd = self.incidents.tick(now)
            if upd:
                self._emit_crash(upd, now)
            self._stop.wait(0.05)  # ~20 Hz

    def _emit_crash(self, upd, ts) -> None:
        inc = upd.incident
        payload = {
            "incident_id": inc.incident_id,
            "status": upd.status,
            "severity": inc.severity,
            "peak_g": inc.peak_g,
            "reasons": inc.reasons,
            "agree_count": len(inc.reasons),
            "cancel_window_s": upd.cancel_window_s,
            "location": inc.location,
            "ts_detected": _r(inc.detected_at),
        }
        self._emit(E.CRASH, payload, ts)
        if upd.status == E.DETECTED:
            print(f"[CRASH] {inc.severity} peak={inc.peak_g}g reasons={inc.reasons} "
                  f"-> cancel within {upd.cancel_window_s:.0f}s ('c' to cancel)")
        else:
            print(f"[CRASH] {inc.incident_id} -> {upd.status}")

    # ── heartbeat ─────────────────────────────────────────────────────
    def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            now = time.time()
            payload = {
                "uptime_s": _r(now - self._start_t, 1),
                "fps": _r(self._fps, 1),
                "target_fps": self.t.fps_idle if self._duty_state == "idle" else self.t.fps_full,
                "duty": self._duty_state,
                "camera_ok": self._camera_ok,
                "sensors_ok": bool(self.ssrc.connected),
                "calibrated": self.calib.ready,
                "speed_mps": self._get_speed(),
                "link": self.uplink.mode,                    # online | degraded | offline
                "pending": self.uplink.pending(),            # un-acked backlog in the edge outbox
                "last_ack_age_s": self.uplink.last_ack_age(),
            }
            self._emit(E.HEARTBEAT, payload, now)
            self._stop.wait(self.t.heartbeat_s)
