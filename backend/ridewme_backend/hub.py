"""Fleet-app fan-out: keeps the set of subscribed fleet WebSockets and broadcasts
state/event deltas to all of them. Relay only."""

from __future__ import annotations

import json
from typing import Any


class Hub:
    def __init__(self) -> None:
        self._subs: set = set()

    async def register(self, ws) -> None:
        self._subs.add(ws)

    def unregister(self, ws) -> None:
        self._subs.discard(ws)

    @property
    def count(self) -> int:
        return len(self._subs)

    async def broadcast(self, msg: dict[str, Any]) -> None:
        text = json.dumps(msg, separators=(",", ":"))
        dead = []
        for ws in list(self._subs):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._subs.discard(ws)
