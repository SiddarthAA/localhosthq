"""Tamper-evident chain verification — DB-free (no Postgres needed).

This is the core L7 guarantee: a valid signed chain verifies; flipping a stored
byte or dropping an event makes verify_rows report the broken seq."""

import json
import sys
from pathlib import Path

from nacl.signing import SigningKey

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli"))
from ridewme.events import DROWSINESS, HELLO  # noqa: E402
from ridewme.signing import EventChain  # noqa: E402

from ridewme_backend.chain import verify_rows  # noqa: E402


def _rows_and_keys():
    key = SigningKey(bytes(range(32)))
    ch = EventChain(key, "driver-1", "s-chain")
    evs = [
        ch.make(HELLO, {"pubkey": ch.pubkey_b64}),
        ch.make(DROWSINESS, {"level": "warn", "score": 58.3}),
        ch.make(DROWSINESS, {"level": "alarm", "score": 90.0}),
    ]
    rows = [(e["session_id"], e["seq"], json.dumps(e, separators=(",", ":"))) for e in evs]
    return rows, {"s-chain": ch.pubkey_b64}


def test_valid_chain_verifies():
    rows, keys = _rows_and_keys()
    res = verify_rows(rows, keys)
    assert res["ok"] is True and res["count"] == 3 and res["broken_at"] is None


def test_tampered_row_breaks():
    rows, keys = _rows_and_keys()
    sid, seq, body = rows[1]
    ev = json.loads(body)
    ev["payload"]["score"] = 12.0                      # flip one value
    rows[1] = (sid, seq, json.dumps(ev, separators=(",", ":")))
    res = verify_rows(rows, keys)
    assert res["ok"] is False and res["broken_at"] == 1 and res["reason"] == "signature_mismatch"


def test_dropped_event_breaks_chain():
    rows, keys = _rows_and_keys()
    res = verify_rows([rows[0], rows[2]], keys)          # remove seq 1
    assert res["ok"] is False and res["broken_at"] == 2 and res["reason"] == "chain_break"
