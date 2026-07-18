"""Frozen golden vector — MUST stay identical to backend/tests/test_verify_golden.py.
If canonical serialization drifts on either side, one of these fails and signatures
would stop verifying across processes."""

import base64

from nacl.signing import SigningKey

from ridewme import events as E
from ridewme.signing import EventChain, sign_canonical

SEED = bytes(range(32))
PUBKEY = "A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg="
CANON = (
    '{"driver_id":"driver-1","payload":{"kind":"transition","level":"warn",'
    '"score":58.3},"prev_sig":"cHJldg==","seq":7,"session_id":"s-golden",'
    '"ts":1721300000.123,"type":"drowsiness","v":1}'
)
SIG = "NADvBd0C4emiv3zqesjUZHEOgty3UPfBnWZepLitvwi+WLZgztvQO/5RhkRxm3wYYRC9vDMBLdppqDaY2+g3Bg=="


def _golden_unsigned():
    return E.envelope(
        type=E.DROWSINESS, driver_id="driver-1", session_id="s-golden",
        seq=7, ts=1721300000.123, prev_sig="cHJldg==",
        payload={"level": "warn", "score": 58.3, "kind": "transition"},
    )


def test_canonical_bytes_frozen():
    assert E.canonical_bytes(_golden_unsigned()).decode() == CANON


def test_signature_frozen():
    key = SigningKey(SEED)
    assert base64.b64encode(bytes(key.verify_key)).decode() == PUBKEY
    assert sign_canonical(key, _golden_unsigned()) == SIG


def test_chain_roundtrip_and_linkage():
    key = SigningKey(SEED)
    chain = EventChain(key, "driver-1", "s-1")
    hello = chain.make(E.HELLO, {"pubkey": chain.pubkey_b64})
    e1 = chain.make(E.HEARTBEAT, {"uptime_s": 1.0})
    e2 = chain.make(E.DROWSINESS, {"level": "notice", "score": 22.0})
    assert hello["seq"] == 0 and hello["prev_sig"] == ""
    assert e1["prev_sig"] == hello["sig"]     # chain links
    assert e2["prev_sig"] == e1["sig"]
    # every event self-verifies against the session key
    vk = key.verify_key
    for ev in (hello, e1, e2):
        vk.verify(E.canonical_bytes(ev), base64.b64decode(ev["sig"]))
