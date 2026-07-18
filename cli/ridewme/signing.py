"""Ed25519 key management + the tamper-evident event chain (CONTRACT §3).

The daemon generates a keypair on first run; the private seed stays on the edge
(gitignored under cli/keys/). Every event is signed and chained: each event's
`prev_sig` equals the previous event's `sig`, so the whole stream is
tamper-evident and the backend can detect any break.
"""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

from nacl.signing import SigningKey

from . import events


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def load_or_create_key(path: str | Path) -> SigningKey:
    """Load the Ed25519 signing seed from `path`, creating it (0600) if absent."""
    p = Path(path)
    if p.exists():
        return SigningKey(p.read_bytes())
    p.parent.mkdir(parents=True, exist_ok=True)
    key = SigningKey.generate()
    # Write the 32-byte seed with restrictive permissions.
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(bytes(key))
    return key


def sign_canonical(key: SigningKey, unsigned_event: dict[str, Any]) -> str:
    """Return base64 Ed25519 signature over canonical_bytes(unsigned_event)."""
    return b64(key.sign(events.canonical_bytes(unsigned_event)).signature)


class EventChain:
    """Stateful signer that builds monotonically-sequenced, chained signed events.

    Not thread-safe by construction — the daemon funnels all emissions through a
    single outbound queue, so `make()` is only ever called from one place.
    """

    def __init__(self, key: SigningKey, driver_id: str, session_id: str):
        self._key = key
        self.driver_id = driver_id
        self.session_id = session_id
        self.seq = 0
        self.prev_sig = ""  # genesis: hello has prev_sig == ""

    @property
    def pubkey_b64(self) -> str:
        return b64(bytes(self._key.verify_key))

    def make(self, type: str, payload: dict[str, Any], ts: float | None = None) -> dict[str, Any]:
        ev = events.envelope(
            type=type,
            driver_id=self.driver_id,
            session_id=self.session_id,
            seq=self.seq,
            ts=time.time() if ts is None else ts,
            prev_sig=self.prev_sig,
            payload=payload,
        )
        ev["sig"] = sign_canonical(self._key, ev)
        self.prev_sig = ev["sig"]
        self.seq += 1
        return ev
