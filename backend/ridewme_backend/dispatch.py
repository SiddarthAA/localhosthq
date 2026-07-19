"""Emergency-services dispatch — the ONLY action that fires on `crash.confirmed`
(design §8). The daemon owns the *decision* (runs the countdown, emits the terminal
event); the backend owns *delivery* (it holds the contacts/integrations). This keeps
the invariant intact: no crash logic or timers in the backend.

Hackathon stub: it logs the dispatch clearly and keeps an audit list. Swap `notify`
for a real webhook / SMS / responder API at deploy time — the trigger contract
(fire on `confirmed`, never before) does not change.
"""

from __future__ import annotations

import time
from typing import Any

from .events import CONFIRMED, CRASH

# Hardcoded nearest responder for the demo (swap for a geo-lookup at deploy time).
HOSPITAL = {
    "name": "Apollo Spectra Hospitals — Koramangala, Bengaluru",
    "address": "143, 1st Cross Rd, near Nagarjuna Hotel, KHB Colony, 5th Block, "
               "Koramangala, Bengaluru, Karnataka 560095",
    "emergency_line": "1066",
}


def should_dispatch(ev: dict[str, Any], verified: bool) -> bool:
    """Emergency dispatch fires ONLY on a *verified* crash.confirmed (design §3, §8).
    Never on unconfirmed, cancelled, an unverified event, or any drowsiness event."""
    return (
        bool(verified)
        and ev.get("type") == CRASH
        and (ev.get("payload") or {}).get("status") == CONFIRMED
    )


class Dispatcher:
    def __init__(self) -> None:
        self.dispatched: list[dict[str, Any]] = []

    def notify(self, payload: dict[str, Any], driver_id: str | None) -> dict[str, Any]:
        record = {
            "incident_id": payload.get("incident_id"),
            "driver_id": driver_id,
            "severity": payload.get("severity"),
            "location": payload.get("location"),
            "responder": HOSPITAL,
            "dispatched_at": round(time.time(), 3),
        }
        print(f"[DISPATCH] Fleet manager notified · contacting first responders & hospitals "
              f"→ {HOSPITAL['name']} · incident={record['incident_id']} "
              f"driver={driver_id} severity={record['severity']}")
        self.dispatched.append(record)
        return record
