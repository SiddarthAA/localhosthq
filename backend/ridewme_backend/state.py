"""Current per-driver state, derived from the event stream. Pure bookkeeping —
no decisions. Serialized into the DriverState shape the fleet app renders
(CONTRACT §5.1)."""

from __future__ import annotations

import time
from typing import Any

from .events import CANCELLED, CONFIRMED, CRASH, DROWSINESS, HEARTBEAT, UNCONFIRMED


class StateStore:
    def __init__(self, online_timeout_s: float = 15.0):
        self._d: dict[str, dict[str, Any]] = {}
        self._timeout = online_timeout_s

    @staticmethod
    def _new(driver_id: str) -> dict[str, Any]:
        return {
            "driver_id": driver_id, "session_id": None, "level": "awake", "score": 0.0,
            "gated": False, "duty": "full", "fps": 0.0, "speed_mps": None,
            "calibrated": False, "last_event_ts": None, "last_seen": 0.0,
            "link": "online", "pending": 0, "active_incident": None,
        }

    def apply(self, ev: dict[str, Any], verified: bool = True) -> dict[str, Any]:
        did = ev.get("driver_id")
        st = self._d.get(did) or self._new(did)
        self._d[did] = st
        st["last_seen"] = time.time()
        st["session_id"] = ev.get("session_id")
        st["last_event_ts"] = ev.get("ts")
        p = ev.get("payload") or {}
        typ = ev.get("type")
        if typ == DROWSINESS:
            st["level"] = p.get("level", st["level"])
            st["score"] = p.get("score", st["score"])
            st["gated"] = p.get("gated", st["gated"])
            st["calibrated"] = p.get("calibrated", st["calibrated"])
        elif typ == HEARTBEAT:
            st["duty"] = p.get("duty", st["duty"])
            st["fps"] = p.get("fps", st["fps"])
            st["speed_mps"] = p.get("speed_mps", st["speed_mps"])
            st["calibrated"] = p.get("calibrated", st["calibrated"])
            st["link"] = p.get("link", st["link"])
            st["pending"] = p.get("pending", st["pending"])
        elif typ == CRASH:
            self._apply_crash(st, ev, p)
        return st

    def _apply_crash(self, st: dict, ev: dict, p: dict) -> None:
        status = p.get("status")
        if status == UNCONFIRMED:
            st["active_incident"] = {
                "incident_id": p.get("incident_id"), "driver_id": ev.get("driver_id"),
                "severity": p.get("severity"), "status": status, "peak_g": p.get("peak_g"),
                "jerk": p.get("jerk"), "signals_fired": p.get("signals_fired"),
                "location": p.get("location"), "window_seconds": p.get("window_seconds"),
                "fatigue_context": p.get("fatigue_context"),
                "detected_at": p.get("ts_detected", ev.get("ts")), "resolved_at": None,
            }
        else:
            ai = st.get("active_incident")
            if ai and ai.get("incident_id") == p.get("incident_id"):
                ai["status"] = status
                ai["resolved_at"] = ev.get("ts")
                if p.get("reason"):
                    ai["reason"] = p.get("reason")
                if p.get("final_motion"):
                    ai["final_motion"] = p.get("final_motion")
                if status == CANCELLED:
                    st["active_incident"] = None  # cleared; confirmed stays visible

    def serialize(self, st: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        out = {k: v for k, v in st.items() if k != "last_seen"}
        out["online"] = (now - st["last_seen"]) < self._timeout
        out["updated_at"] = round(now, 3)
        return out

    def snapshot(self) -> list[dict[str, Any]]:
        return [self.serialize(s) for s in self._d.values()]

    def get(self, driver_id: str) -> dict[str, Any] | None:
        st = self._d.get(driver_id)
        return self.serialize(st) if st else None

    def driver_ids(self) -> list[str]:
        return list(self._d.keys())
