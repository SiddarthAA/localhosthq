"""Ed25519 verification — the backend half of the trust guarantee (CONTRACT §3).

Signing lives in the daemon, verification here; both are Python so the canonical
bytes match exactly. The frontend only *displays* the verification status.
"""

from __future__ import annotations

import base64
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from .events import canonical_bytes


def verify_sig(pubkey_b64: str, event: dict[str, Any]) -> bool:
    """True iff `event['sig']` is a valid Ed25519 signature over its canonical bytes."""
    try:
        vk = VerifyKey(base64.b64decode(pubkey_b64))
        vk.verify(canonical_bytes(event), base64.b64decode(event["sig"]))
        return True
    except (BadSignatureError, KeyError, ValueError, TypeError):
        return False
