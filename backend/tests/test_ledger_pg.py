"""Postgres ledger integration test. Skips cleanly when no DB is reachable, so
`pytest` stays green without Docker; runs for real once `database/` is up."""

import os
import sys
import uuid
from pathlib import Path

import pytest
from nacl.signing import SigningKey

pytest.importorskip("psycopg")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli"))
from ridewme.events import DROWSINESS, HELLO  # noqa: E402
from ridewme.signing import EventChain  # noqa: E402

from ridewme_backend.ledger import Ledger  # noqa: E402

DSN = os.getenv("DATABASE_URL", "postgresql://ridewme:ridewme@127.0.0.1:5432/ridewme")


def _ledger():
    try:
        return Ledger(DSN, connect_retries=1)
    except Exception as e:  # no Postgres running
        pytest.skip(f"Postgres not available: {e}")


def _fresh_ids():
    tag = uuid.uuid4().hex[:8]
    return f"pgtest-{tag}", f"s-pgtest-{tag}"


def test_append_and_verify_roundtrip():
    led = _ledger()
    driver, sid = _fresh_ids()
    ch = EventChain(SigningKey(bytes(range(32))), driver, sid)
    ok, err = led.append(ch.make(HELLO, {"pubkey": ch.pubkey_b64}))
    assert ok, err
    ok, err = led.append(ch.make(DROWSINESS, {"level": "warn", "score": 58.3}))
    assert ok, err
    res = led.verify_chain(driver)
    assert res["ok"] is True and res["count"] == 2


def test_unknown_session_rejected():
    led = _ledger()
    driver, sid = _fresh_ids()
    ch = EventChain(SigningKey(bytes(range(32))), driver, sid)
    ok, _ = led.append(ch.make(DROWSINESS, {"level": "warn"}))   # no hello first
    assert ok is False
