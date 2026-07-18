"""The single upward WebSocket: daemon -> backend, draining the durable outbox.

Ships un-acked events from the Outbox at-least-once, deleting each only when the
backend acks (session_id, seq). Reconnects on drop; the outbox makes loss
impossible across crashes / dead zones / backend restarts. In-flight rows are
resent if their ack doesn't arrive in time. Exposes link mode (online / degraded /
offline) + backlog so the daemon can report sync status. Never blocks the daemon.
"""

from __future__ import annotations

import json
import threading
import time

from .events import to_wire

ONLINE, DEGRADED, OFFLINE = "online", "degraded", "offline"


class Uplink:
    _WINDOW = 200          # max events in flight at once
    _RESEND_TIMEOUT = 5.0  # resend an un-acked in-flight event after this many seconds

    def __init__(self, cfg, outbox):
        self.url = cfg.ingest_ws_url
        self.token = cfg.ingest_token
        self._outbox = outbox
        self._degraded_at = cfg.tuning.link_degraded_pending
        self._hello: dict | None = None
        self._in_flight: dict[tuple[str, int], float] = {}   # (session, seq) -> sent_ts
        self._stop = False
        self.connected = False
        self._last_ack_ts: float | None = None

    # ── public status (read by the daemon's heartbeat) ────────────────
    def start(self, hello: dict) -> None:
        self._hello = hello
        threading.Thread(target=self._loop, name="uplink", daemon=True).start()

    @property
    def mode(self) -> str:
        if not self.connected:
            return OFFLINE
        return DEGRADED if self._outbox.count() > self._degraded_at else ONLINE

    def pending(self) -> int:
        return self._outbox.count()

    def last_ack_age(self) -> float | None:
        return None if self._last_ack_ts is None else round(time.time() - self._last_ack_ts, 1)

    def close(self) -> None:
        self._stop = True

    # ── delivery loop ─────────────────────────────────────────────────
    def _connect(self):
        import websocket  # websocket-client

        header = [f"Authorization: Bearer {self.token}"] if self.token else []
        conn = websocket.create_connection(self.url, timeout=5, header=header)
        conn.settimeout(0.3)
        if self._hello is not None:
            conn.send(to_wire(self._hello))   # (re)register the current session's pubkey
        return conn

    def _loop(self) -> None:
        try:
            import websocket
        except ImportError:
            print("[uplink] websocket-client not installed; uplink disabled.")
            return

        while not self._stop:
            try:
                conn = self._connect()
                self.connected = True
                self._in_flight.clear()
            except Exception:
                self.connected = False
                time.sleep(1.0)
                continue
            try:
                while not self._stop:
                    self._pump(conn)
                    self._drain_acks(conn, websocket)
            except Exception:
                self.connected = False
                try:
                    conn.close()
                except Exception:
                    pass
                self._in_flight.clear()
                time.sleep(1.0)

    def _pump(self, conn) -> None:
        now = time.time()
        # Give up on in-flight rows whose ack was lost -> they become resendable.
        for key, sent in list(self._in_flight.items()):
            if now - sent > self._RESEND_TIMEOUT:
                del self._in_flight[key]
        for sid, seq, body in self._outbox.pending(self._WINDOW, set(self._in_flight.keys())):
            conn.send(body)
            self._in_flight[(sid, seq)] = now

    def _drain_acks(self, conn, websocket) -> None:
        while True:
            try:
                msg = conn.recv()
            except websocket.WebSocketTimeoutException:
                return
            if msg == "":
                raise ConnectionError("closed")
            try:
                ack = json.loads(msg)
            except ValueError:
                continue
            sid, seq = ack.get("session_id"), ack.get("ack")
            if sid is not None and seq is not None:
                self._outbox.ack(sid, seq)              # delivered -> drop from durable store
                self._in_flight.pop((sid, seq), None)
                self._last_ack_ts = time.time()
