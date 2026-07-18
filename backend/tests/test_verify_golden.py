"""Frozen golden vector — MUST stay identical to cli/tests/test_signing_golden.py.
Proves the daemon's signature verifies here and that any tamper is caught."""

from ridewme_backend import events as E
from ridewme_backend.verify import verify_sig

PUBKEY = "A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg="
CANON = (
    '{"driver_id":"driver-1","payload":{"kind":"transition","level":"warn",'
    '"score":58.3},"prev_sig":"cHJldg==","seq":7,"session_id":"s-golden",'
    '"ts":1721300000.123,"type":"drowsiness","v":1}'
)
SIG = "NADvBd0C4emiv3zqesjUZHEOgty3UPfBnWZepLitvwi+WLZgztvQO/5RhkRxm3wYYRC9vDMBLdppqDaY2+g3Bg=="


def _signed():
    return {
        "v": 1, "type": "drowsiness", "driver_id": "driver-1", "session_id": "s-golden",
        "seq": 7, "ts": 1721300000.123, "prev_sig": "cHJldg==",
        "payload": {"level": "warn", "score": 58.3, "kind": "transition"}, "sig": SIG,
    }


def test_backend_canonical_matches_daemon():
    assert E.canonical_bytes(_signed()).decode() == CANON


def test_daemon_signature_verifies_here():
    assert verify_sig(PUBKEY, _signed()) is True


def test_tamper_is_rejected():
    ev = _signed()
    ev["payload"]["score"] = 59.9         # flip one value
    assert verify_sig(PUBKEY, ev) is False
