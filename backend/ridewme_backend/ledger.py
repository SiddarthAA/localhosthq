"""The tamper-evident audit ledger — Postgres (local Docker now, managed cloud later).

Same guarantees as before: every event is verified on ingest and appended to a
signature chain; `verify_chain()` re-derives canonical bytes from *stored* data and
re-checks every signature + link, so editing any row makes it report the broken
seq. Swapping SQLite → Postgres is contained precisely because the backend is a
dumb store — the decision engine (cli/) is untouched. Cloud is just a different DSN.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import psycopg

from .chain import verify_rows
from .events import CRASH, HELLO, UNCONFIRMED
from .verify import verify_sig

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS sessions (
         session_id TEXT PRIMARY KEY, driver_id TEXT NOT NULL,
         pubkey TEXT NOT NULL, started_at DOUBLE PRECISION)""",
    """CREATE TABLE IF NOT EXISTS events (
         session_id TEXT NOT NULL, seq INTEGER NOT NULL, driver_id TEXT, type TEXT,
         ts DOUBLE PRECISION, prev_sig TEXT, sig TEXT, body TEXT NOT NULL, verified BOOLEAN,
         PRIMARY KEY (session_id, seq))""",
    "CREATE INDEX IF NOT EXISTS idx_events_driver ON events (driver_id, ts)",
    "CREATE INDEX IF NOT EXISTS idx_events_dtype ON events (driver_id, type, ts)",
]


class Ledger:
    def __init__(self, dsn: str, connect_retries: int = 10):
        self._lock = threading.Lock()
        self._conn = self._connect(dsn, connect_retries)
        self._ensure_schema()

    @staticmethod
    def _connect(dsn: str, retries: int):
        last: Exception | None = None
        for _ in range(max(1, retries)):
            try:
                return psycopg.connect(dsn, autocommit=True)
            except Exception as e:  # Postgres may still be booting
                last = e
                time.sleep(1.0)
        raise RuntimeError(f"cannot connect to Postgres ({dsn}): {last}")

    def _ensure_schema(self) -> None:
        with self._lock:
            for stmt in _SCHEMA:
                self._conn.execute(stmt)

    # ── ingest ────────────────────────────────────────────────────────
    def append(self, ev: dict[str, Any]) -> tuple[bool, str | None]:
        with self._lock:
            return self._append(ev)

    def _append(self, ev: dict[str, Any]) -> tuple[bool, str | None]:
        sid, seq, typ = ev.get("session_id"), ev.get("seq"), ev.get("type")
        if sid is None or seq is None or typ is None:
            return (False, "missing envelope")

        existing = self._conn.execute(
            "SELECT verified FROM events WHERE session_id=%s AND seq=%s", (sid, seq)
        ).fetchone()
        if existing is not None:  # idempotent: reconnect / hello-resend
            return (bool(existing[0]), None)

        if typ == HELLO:
            pubkey = (ev.get("payload") or {}).get("pubkey")
            if not pubkey:
                return (False, "hello missing pubkey")
            ok = verify_sig(pubkey, ev)  # self-signed
            self._conn.execute(
                "INSERT INTO sessions (session_id, driver_id, pubkey, started_at) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (session_id) DO UPDATE SET pubkey=EXCLUDED.pubkey, "
                "driver_id=EXCLUDED.driver_id",
                (sid, ev.get("driver_id"), pubkey, (ev.get("payload") or {}).get("started_at")),
            )
            self._store(ev, ok)
            return (ok, None if ok else "bad hello signature")

        srow = self._conn.execute(
            "SELECT pubkey FROM sessions WHERE session_id=%s", (sid,)
        ).fetchone()
        if srow is None:
            return (False, "unknown session (no hello yet)")
        ok = verify_sig(srow[0], ev)
        if seq > 0:
            prev = self._conn.execute(
                "SELECT sig FROM events WHERE session_id=%s AND seq=%s", (sid, seq - 1)
            ).fetchone()
            if prev is not None and prev[0] != ev.get("prev_sig"):
                ok = False
        self._store(ev, ok)
        return (ok, None if ok else "verification failed")

    def _store(self, ev: dict[str, Any], ok: bool) -> None:
        self._conn.execute(
            "INSERT INTO events (session_id, seq, driver_id, type, ts, prev_sig, sig, body, verified) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id, seq) DO NOTHING",
            (ev["session_id"], ev["seq"], ev.get("driver_id"), ev.get("type"), ev.get("ts"),
             ev.get("prev_sig"), ev.get("sig"), json.dumps(ev, separators=(",", ":")), ok),
        )

    # ── queries ───────────────────────────────────────────────────────
    def events_by_driver(self, driver_id: str, limit: int = 100, type: str | None = None):
        q = "SELECT body FROM events WHERE driver_id=%s"
        args: list = [driver_id]
        if type:
            q += " AND type=%s"
            args.append(type)
        q += " ORDER BY ts DESC LIMIT %s"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [json.loads(r[0]) for r in rows]

    def ledger(self, driver_id: str, limit: int = 200):
        with self._lock:
            rows = self._conn.execute(
                "SELECT body FROM events WHERE driver_id=%s ORDER BY session_id, seq DESC LIMIT %s",
                (driver_id, limit),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def incidents(self, limit: int = 50):
        with self._lock:
            rows = self._conn.execute(
                "SELECT body FROM events WHERE type=%s ORDER BY ts ASC", (CRASH,)
            ).fetchall()
        cards: dict[str, dict] = {}
        for r in rows:
            ev = json.loads(r[0])
            p = ev["payload"]
            iid = p["incident_id"]
            card = cards.setdefault(iid, {
                "incident_id": iid, "driver_id": ev["driver_id"],
                "severity": p["severity"], "status": p["status"], "peak_g": p.get("peak_g"),
                "jerk": p.get("jerk"), "signals_fired": p.get("signals_fired"),
                "location": p.get("location"), "window_seconds": p.get("window_seconds"),
                "fatigue_context": p.get("fatigue_context"),
                "detected_at": p.get("ts_detected", ev["ts"]), "resolved_at": None,
            })
            card["status"] = p["status"]
            card["severity"] = p["severity"]
            if p.get("reason"):
                card["reason"] = p["reason"]
            if p.get("final_motion"):
                card["final_motion"] = p["final_motion"]
            if p["status"] != UNCONFIRMED:
                card["resolved_at"] = ev["ts"]
        return sorted(cards.values(), key=lambda c: c["detected_at"], reverse=True)[:limit]

    def verify_chain(self, driver_id: str) -> dict[str, Any]:
        with self._lock:
            pubkeys = {
                r[0]: r[1] for r in self._conn.execute(
                    "SELECT session_id, pubkey FROM sessions WHERE driver_id=%s", (driver_id,)
                ).fetchall()
            }
            rows = self._conn.execute(
                "SELECT session_id, seq, body FROM events WHERE driver_id=%s ORDER BY session_id, seq",
                (driver_id,),
            ).fetchall()
        return verify_rows(rows, pubkeys)
