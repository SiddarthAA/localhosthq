"""Event schema — MIRROR of cli/ridewme/events.py.

`canonical_bytes()` MUST match the daemon's copy byte-for-byte or signatures
won't verify. The frozen golden vector in tests/ (identical on both sides) guards
against drift. Keep this file in sync with the daemon's. See CONTRACT.md §2.
"""

from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = 1

HELLO = "hello"
HEARTBEAT = "heartbeat"
DROWSINESS = "drowsiness"
CRASH = "crash"

AWAKE = "awake"
NOTICE = "notice"
WARN = "warn"
ALARM = "alarm"

DETECTED = "detected"
CONFIRMED = "confirmed"
DISPATCHED = "dispatched"
CANCELLED = "cancelled"


def canonical_bytes(event: dict[str, Any]) -> bytes:
    """Deterministic bytes signed/verified for `event`. Excludes the `sig` field."""
    body = {k: v for k, v in event.items() if k != "sig"}
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
