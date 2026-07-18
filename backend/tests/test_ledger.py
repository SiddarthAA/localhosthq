"""The tamper-evident ledger: a valid chain verifies; flipping a stored byte
makes verify_chain report the broken seq (the L7 tamper demo)."""

import base64
import json
import sys
from pathlib import Path

from nacl.signing import SigningKey

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli"))
from ridewme.events import (CRASH, DROWSINESS, HEARTBEAT, HELLO,  # noqa: E402
                               canonical_bytes)
from ridewme.signing import EventChain  # noqa: E402

from ridewme_backend.ledger import Ledger  # noqa: E402


def _chain():
    key = SigningKey(bytes(range(32)))
    return EventChain(key, "driver-1", "s-led")


def _ledger(tmp_path):
    return Ledger(str(tmp_path / "t.db"))


def test_valid_chain_verifies(tmp_path):
    led = _ledger(tmp_path)
    ch = _chain()
    led.append(ch.make(HELLO, {"pubkey": ch.pubkey_b64}))
    for _ in range(5):
        ok, err = led.append(ch.make(HEARTBEAT, {"uptime_s": 1.0}))
        assert ok, err
    res = led.verify_chain("driver-1")
    assert res["ok"] is True
    assert res["count"] == 6
    assert res["broken_at"] is None


def test_unknown_session_is_rejected(tmp_path):
    led = _ledger(tmp_path)
    ch = _chain()
    ok, err = led.append(ch.make(HEARTBEAT, {"uptime_s": 1.0}))  # no hello first
    assert ok is False


def test_tampered_row_breaks_verification(tmp_path):
    led = _ledger(tmp_path)
    ch = _chain()
    led.append(ch.make(HELLO, {"pubkey": ch.pubkey_b64}))
    led.append(ch.make(DROWSINESS, {"level": "warn", "score": 58.3}))
    led.append(ch.make(DROWSINESS, {"level": "alarm", "score": 90.0}))
    assert led.verify_chain("driver-1")["ok"] is True

    # Tamper: rewrite the stored body of seq 1 (flip the score) directly in SQLite.
    row = led._conn.execute(
        "SELECT body FROM events WHERE session_id=? AND seq=1", ("s-led",)
    ).fetchone()
    ev = json.loads(row["body"])
    ev["payload"]["score"] = 12.0
    led._conn.execute(
        "UPDATE events SET body=? WHERE session_id=? AND seq=1",
        (json.dumps(ev, separators=(",", ":")), "s-led"),
    )
    led._conn.commit()

    res = led.verify_chain("driver-1")
    assert res["ok"] is False
    assert res["broken_at"] == 1
    assert res["reason"] == "signature_mismatch"


def test_incident_cards(tmp_path):
    led = _ledger(tmp_path)
    ch = _chain()
    led.append(ch.make(HELLO, {"pubkey": ch.pubkey_b64}))
    led.append(ch.make(CRASH, {
        "incident_id": "crash-s-led-1", "status": "detected", "severity": "moderate",
        "peak_g": 4.3, "reasons": ["accel_spike", "rotation"], "cancel_window_s": 10,
        "location": {"lat": 1.0, "lon": 2.0}, "ts_detected": 1.0,
    }))
    led.append(ch.make(CRASH, {
        "incident_id": "crash-s-led-1", "status": "confirmed", "severity": "moderate",
        "peak_g": 4.3, "reasons": ["accel_spike", "rotation"], "cancel_window_s": 10,
        "location": {"lat": 1.0, "lon": 2.0}, "ts_detected": 1.0,
    }))
    cards = led.incidents()
    assert len(cards) == 1
    assert cards[0]["status"] == "confirmed"
    assert cards[0]["resolved_at"] is not None
