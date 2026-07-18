"""The naive baseline detector — the strawman for the side-by-side demo.

No calibration, no corroboration, no persistence, no context: it alarms the
instant EAR drops below a fixed global threshold. This is the "beeps at every
blink" behavior that makes drivers cover the camera. Ship it only as `--naive`
to contrast against the real engine (L1-L5).
"""

from __future__ import annotations

from .events import ALARM, AWAKE
from .signals import RawFeatures

_GLOBAL_CLOSED_EAR = 0.20


class NaiveDetector:
    def update(self, raw: RawFeatures) -> str:
        closed = raw.face_present and raw.ear is not None and raw.ear < _GLOBAL_CLOSED_EAR
        return ALARM if closed else AWAKE
