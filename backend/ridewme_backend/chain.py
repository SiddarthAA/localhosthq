"""Pure signature-chain verification — no database, so it unit-tests directly.

Given the stored event rows (in `(session_id, seq)` order) and the per-session
public keys, re-derive canonical bytes from each stored body and re-check every
signature + prev_sig link. Any failure returns the broken seq. The Postgres ledger
just fetches rows and calls this.
"""

from __future__ import annotations

import json
import time
from typing import Any, Iterable

from .verify import verify_sig


def _result(ok: bool, count: int, seq: int | None = None, reason: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": ok, "count": count, "broken_at": seq, "checked_at": round(time.time(), 3)}
    if reason:
        out["reason"] = reason
    return out


def verify_rows(rows: Iterable[tuple], pubkeys: dict[str, str]) -> dict[str, Any]:
    """`rows`: iterable of (session_id, seq, body) ordered by (session_id, seq),
    where `body` is the exact signed JSON (str or dict). `pubkeys`: session_id -> pubkey."""
    count = 0
    expected_prev: dict[str, str] = {}
    for session_id, seq, body in rows:
        ev = json.loads(body) if isinstance(body, str) else body
        pubkey = pubkeys.get(session_id)
        if pubkey is None or not verify_sig(pubkey, ev):
            return _result(False, count, seq, "signature_mismatch")
        if ev.get("prev_sig", "") != expected_prev.get(session_id, ""):
            return _result(False, count, seq, "chain_break")
        expected_prev[session_id] = ev.get("sig", "")
        count += 1
    return _result(True, count)
