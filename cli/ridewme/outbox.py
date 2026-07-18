"""Durable store-and-forward outbox on the edge (SQLite / WAL).

Every signed event the daemon emits is persisted here *before* it's sent, and
removed only once the backend acks it. This is what makes the edge resilient: a
crash, a dead zone, or a backend restart can't lose events — un-acked rows survive
on disk and are replayed on reconnect. At-least-once delivery; the backend dedups
by (session_id, seq). The edge is the source of truth; the backend is a replica it
syncs into.
"""

from __future__ import annotations

import sqlite3
import threading
import time


class Outbox:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")     # durable + concurrent-friendly
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS outbox ("
            "session_id TEXT NOT NULL, seq INTEGER NOT NULL, body TEXT NOT NULL, "
            "created_at REAL NOT NULL, PRIMARY KEY (session_id, seq))"
        )
        self._conn.commit()

    def put(self, session_id: str, seq: int, body: str) -> None:
        """Persist an event for delivery. Idempotent per (session_id, seq)."""
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO outbox (session_id, seq, body, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, seq, body, time.time()),
            )
            self._conn.commit()

    def pending(self, limit: int, exclude) -> list[tuple[str, int, str]]:
        """Oldest-first un-acked rows not currently in flight (`exclude`)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT session_id, seq, body FROM outbox ORDER BY created_at, rowid LIMIT ?",
                (limit + len(exclude),),
            ).fetchall()
        out: list[tuple[str, int, str]] = []
        for sid, seq, body in rows:
            if (sid, seq) in exclude:
                continue
            out.append((sid, seq, body))
            if len(out) >= limit:
                break
        return out

    def ack(self, session_id: str, seq: int) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM outbox WHERE session_id=? AND seq=?", (session_id, seq)
            )
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]

    def oldest_age(self) -> float | None:
        with self._lock:
            row = self._conn.execute("SELECT MIN(created_at) FROM outbox").fetchone()
        return None if row[0] is None else time.time() - row[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
