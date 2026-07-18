"""The tamper-evident audit ledger (SQLite + Ed25519 signature chain).

Every event is verified on ingest and appended. `verify_chain()` re-derives the
canonical bytes from *stored* data and re-checks every signature and chain link —
so editing any byte in the DB (the tamper demo) makes it return the broken seq.
The backend makes no decisions; it only proves what the daemon said.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from .events import CANCELLED, CRASH, DETECTED, HELLO
from .verify import verify_sig


class Ledger:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
              session_id TEXT PRIMARY KEY, driver_id TEXT, pubkey TEXT, started_at REAL);
            CREATE TABLE IF NOT EXISTS events(
              session_id TEXT, seq INTEGER, driver_id TEXT, type TEXT, ts REAL,
              prev_sig TEXT, sig TEXT, body TEXT, verified INTEGER,
              PRIMARY KEY(session_id, seq));
            CREATE INDEX IF NOT EXISTS idx_events_driver ON events(driver_id, ts);
            CREATE INDEX IF NOT EXISTS idx_events_dtype ON events(driver_id, type, ts);
            """
        )
        self._conn.commit()

    # ── ingest ────────────────────────────────────────────────────────
    def append(self, ev: dict[str, Any]) -> tuple[bool, str | None]:
        with self._lock:
            return self._append(ev)

    def _append(self, ev: dict[str, Any]) -> tuple[bool, str | None]:
        sid, seq, typ = ev.get("session_id"), ev.get("seq"), ev.get("type")
        if sid is None or seq is None or typ is None:
            return (False, "missing envelope")

        existing = self._conn.execute(
            "SELECT verified FROM events WHERE session_id=? AND seq=?", (sid, seq)
        ).fetchone()
        if existing is not None:  # idempotent: reconnect/hello-resend
            return (bool(existing["verified"]), None)

        if typ == HELLO:
            pubkey = (ev.get("payload") or {}).get("pubkey")
            if not pubkey:
                return (False, "hello missing pubkey")
            ok = verify_sig(pubkey, ev)  # hello is self-signed
            self._conn.execute(
                "INSERT OR REPLACE INTO sessions VALUES(?,?,?,?)",
                (sid, ev.get("driver_id"), pubkey, (ev.get("payload") or {}).get("started_at")),
            )
            self._store(ev, ok)
            return (ok, None if ok else "bad hello signature")

        srow = self._conn.execute(
            "SELECT pubkey FROM sessions WHERE session_id=?", (sid,)
        ).fetchone()
        if srow is None:
            return (False, "unknown session (no hello yet)")
        ok = verify_sig(srow["pubkey"], ev)
        if seq > 0:
            prev = self._conn.execute(
                "SELECT sig FROM events WHERE session_id=? AND seq=?", (sid, seq - 1)
            ).fetchone()
            if prev is not None and prev["sig"] != ev.get("prev_sig"):
                ok = False
        self._store(ev, ok)
        return (ok, None if ok else "verification failed")

    def _store(self, ev: dict[str, Any], ok: bool) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?,?,?)",
            (ev["session_id"], ev["seq"], ev.get("driver_id"), ev.get("type"), ev.get("ts"),
             ev.get("prev_sig"), ev.get("sig"), json.dumps(ev, separators=(",", ":")),
             1 if ok else 0),
        )
        self._conn.commit()

    # ── queries ───────────────────────────────────────────────────────
    def events_by_driver(self, driver_id: str, limit: int = 100, type: str | None = None):
        q = "SELECT body FROM events WHERE driver_id=?"
        args: list = [driver_id]
        if type:
            q += " AND type=?"
            args.append(type)
        q += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [json.loads(r["body"]) for r in rows]

    def ledger(self, driver_id: str, limit: int = 200):
        with self._lock:
            rows = self._conn.execute(
                "SELECT body FROM events WHERE driver_id=? ORDER BY session_id, seq DESC LIMIT ?",
                (driver_id, limit),
            ).fetchall()
        return [json.loads(r["body"]) for r in rows]

    def incidents(self, limit: int = 50):
        with self._lock:
            rows = self._conn.execute(
                "SELECT body FROM events WHERE type=? ORDER BY ts ASC", (CRASH,)
            ).fetchall()
        cards: dict[str, dict] = {}
        for r in rows:
            ev = json.loads(r["body"])
            p = ev["payload"]
            iid = p["incident_id"]
            card = cards.setdefault(iid, {
                "incident_id": iid, "driver_id": ev["driver_id"],
                "severity": p["severity"], "status": p["status"],
                "peak_g": p["peak_g"], "reasons": p["reasons"],
                "location": p.get("location"),
                "detected_at": p.get("ts_detected", ev["ts"]), "resolved_at": None,
            })
            card["status"] = p["status"]
            card["severity"] = p["severity"]
            if p["status"] in (CANCELLED,) or p["status"] != DETECTED:
                if p["status"] != DETECTED:
                    card["resolved_at"] = ev["ts"]
        ordered = sorted(cards.values(), key=lambda c: c["detected_at"], reverse=True)
        return ordered[:limit]

    def verify_chain(self, driver_id: str) -> dict[str, Any]:
        with self._lock:
            sess = {
                r["session_id"]: r["pubkey"]
                for r in self._conn.execute(
                    "SELECT session_id, pubkey FROM sessions WHERE driver_id=?", (driver_id,)
                ).fetchall()
            }
            rows = self._conn.execute(
                "SELECT session_id, seq, sig, body FROM events WHERE driver_id=? "
                "ORDER BY session_id, seq",
                (driver_id,),
            ).fetchall()

        count = 0
        expected_prev: dict[str, str] = {}
        for r in rows:
            sid = r["session_id"]
            pubkey = sess.get(sid)
            ev = json.loads(r["body"])
            if pubkey is None or not verify_sig(pubkey, ev):
                return self._broken(count, r["seq"], "signature_mismatch")
            prev = expected_prev.get(sid, "")
            if ev.get("prev_sig", "") != prev:
                return self._broken(count, r["seq"], "chain_break")
            expected_prev[sid] = ev.get("sig", "")
            count += 1
        return {"ok": True, "count": count, "broken_at": None, "checked_at": round(time.time(), 3)}

    @staticmethod
    def _broken(count: int, seq: int, reason: str) -> dict[str, Any]:
        return {"ok": False, "count": count, "broken_at": seq,
                "reason": reason, "checked_at": round(time.time(), 3)}
