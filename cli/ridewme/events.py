"""The signed-event schema and its NORMATIVE canonical byte form.

This module is signature-critical. `canonical_bytes()` here MUST byte-for-byte
match the backend's copy (backend/ridewme_backend/events.py) or signatures
won't verify across processes. A frozen golden vector in both test suites guards
against drift. See CONTRACT.md §2.
"""

from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = 1

# Event types (envelope.type)
HELLO = "hello"
HEARTBEAT = "heartbeat"
DROWSINESS = "drowsiness"
CRASH = "crash"

# Drowsiness levels (L5), calm -> loud
AWAKE = "awake"
NOTICE = "notice"
WARN = "warn"
ALARM = "alarm"
LEVELS = (AWAKE, NOTICE, WARN, ALARM)
LEVEL_RANK = {name: i for i, name in enumerate(LEVELS)}

# Crash lifecycle statuses (design §2 ladder). `candidate` is internal (never emitted).
UNCONFIRMED = "unconfirmed"   # Layer 2 passed -> fleet only, window started
CONFIRMED = "confirmed"       # Layer 3 window elapsed, consistent -> emergency services
CANCELLED = "cancelled"       # driver cancel OR sustained normal driving

# Crash cancel reasons
REASON_DRIVER = "driver"
REASON_DEESCALATED = "deescalated_motion"

# Crash severity buckets
MINOR = "minor"
MODERATE = "moderate"
SEVERE = "severe"


def canonical_bytes(event: dict[str, Any]) -> bytes:
    """Deterministic bytes signed/verified for `event`. Excludes the `sig` field.

    Sorted keys, no whitespace, UTF-8. Both the daemon and backend are Python and
    use this exact function, so JSON float round-tripping is stable between them
    (this is precisely why signing+verification both live in Python — CONTRACT §3).
    """
    body = {k: v for k, v in event.items() if k != "sig"}
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def envelope(
    *,
    type: str,
    driver_id: str,
    session_id: str,
    seq: int,
    ts: float,
    prev_sig: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build the unsigned event dict (no `sig` yet). `ts` is rounded to 3 dp."""
    return {
        "v": SCHEMA_VERSION,
        "type": type,
        "driver_id": driver_id,
        "session_id": session_id,
        "seq": seq,
        "ts": round(float(ts), 3),
        "prev_sig": prev_sig,
        "payload": payload,
    }


def to_wire(event: dict[str, Any]) -> str:
    """Serialize a full (signed) event for the wire."""
    return json.dumps(event, separators=(",", ":"), ensure_ascii=False)


def from_wire(text: str) -> dict[str, Any]:
    return json.loads(text)
