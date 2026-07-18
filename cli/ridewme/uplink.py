"""The single upward WebSocket: daemon -> backend, signed events only.

Buffers events in a bounded deque, reconnects on drop, and re-sends the cached
`hello` on every (re)connection so the backend can (re)pin the session pubkey.
The chain stays valid because `hello` is immutable (seq 0, fixed bytes) and the
backend dedups by (session_id, seq). The daemon never blocks on acks.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from .events import to_wire


class Uplink:
    def __init__(self, cfg, maxlen: int = 4000):
        self.url = cfg.ingest_ws_url
        self.token = cfg.ingest_token
        self._buf: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._hello: dict | None = None
        self._stop = False
        self.connected = False

    def start(self, hello: dict) -> None:
        self._hello = hello
        threading.Thread(target=self._loop, daemon=True).start()

    def send(self, event: dict) -> None:
        with self._lock:
            self._buf.append(event)

    def _connect(self):
        import websocket  # websocket-client

        header = [f"Authorization: Bearer {self.token}"] if self.token else []
        conn = websocket.create_connection(self.url, timeout=5, header=header)
        conn.settimeout(1.0)
        conn.send(to_wire(self._hello))
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
            except Exception:
                self.connected = False
                time.sleep(1.0)
                continue
            try:
                while not self._stop:
                    with self._lock:
                        ev = self._buf.popleft() if self._buf else None
                    if ev is not None:
                        try:
                            conn.send(to_wire(ev))
                        except Exception:
                            with self._lock:
                                self._buf.appendleft(ev)  # don't drop it
                            raise
                    else:
                        try:
                            msg = conn.recv()  # drain acks / detect close (1s timeout)
                            if msg == "":
                                raise ConnectionError("closed")
                        except websocket.WebSocketTimeoutException:
                            pass
            except Exception:
                self.connected = False
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(1.0)

    def close(self) -> None:
        self._stop = True
