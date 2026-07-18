#!/usr/bin/env python3
"""Seed the ledger with realistic, cryptographically-signed history for ONE driver.

Single fleet manager, single driver (`driver-1`). Generates ~3 weeks of rides with
drowsiness arcs, a mix of crash outcomes (confirmed dispatch, driver take-backs,
de-escalations), connectivity blips, and the fatigue->crash correlation. Every
event is a REAL signed event (one Ed25519 key, one chain per ride), inserted via
the backend's Ledger.append so signatures verify and `/ledger/verify` stays green.

    ./.venv/bin/python database/seed.py           # clears + seeds
    ./.venv/bin/python database/seed.py --keep     # seed without clearing

Reads DATABASE_URL (repo-root .env) — default local Docker Postgres. Schema is NOT
changed; this only inserts rows.
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "cli"))
sys.path.insert(0, str(REPO / "backend"))

import psycopg  # noqa: E402
from nacl.signing import SigningKey  # noqa: E402

from ridewme import events as E  # noqa: E402
from ridewme.signing import EventChain  # noqa: E402
from ridewme_backend.ledger import Ledger  # noqa: E402

DSN = os.getenv("DATABASE_URL", "postgresql://ridewme:ridewme@127.0.0.1:5432/ridewme")
DRIVER = os.getenv("DRIVER_ID", "driver-1")
KEY = SigningKey(bytes(range(32)))          # one device key for the driver (deterministic)
random.seed(7)

# days_ago, hour, duration(min), fatigue peak score, peak position (0..1),
# crash type | None, crash position (0..1), link profile
RIDES = [
    dict(d=20, h=8.5,  dur=28, peak=12, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=20, h=18.0, dur=35, peak=48, pf=0.60, crash=None,               cf=0.0,  link="online"),
    dict(d=18, h=8.0,  dur=22, peak=8,  pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=17, h=23.0, dur=42, peak=86, pf=0.62, crash="cancel_driver",    cf=0.70, link="flaky"),
    dict(d=15, h=9.0,  dur=30, peak=15, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=14, h=17.5, dur=33, peak=55, pf=0.55, crash=None,               cf=0.0,  link="online"),
    dict(d=12, h=7.5,  dur=25, peak=10, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=11, h=22.0, dur=46, peak=91, pf=0.60, crash="confirmed_severe", cf=0.72, link="online"),
    dict(d=10, h=8.5,  dur=27, peak=20, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=8,  h=13.0, dur=38, peak=42, pf=0.5,  crash="cancel_deesc",     cf=0.55, link="online"),
    dict(d=7,  h=18.5, dur=30, peak=35, pf=0.6,  crash=None,               cf=0.0,  link="flaky"),
    dict(d=5,  h=8.0,  dur=24, peak=12, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=4,  h=16.0, dur=36, peak=63, pf=0.55, crash="confirmed_moderate", cf=0.60, link="online"),
    dict(d=3,  h=9.5,  dur=29, peak=25, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=2,  h=19.0, dur=41, peak=79, pf=0.62, crash="cancel_driver",    cf=0.68, link="online"),
    dict(d=1,  h=8.0,  dur=26, peak=14, pf=0.5,  crash=None,               cf=0.0,  link="online"),
    dict(d=0,  h=7.5,  dur=20, peak=30, pf=0.5,  crash=None,               cf=0.0,  link="online"),
]

CRASH = {  # severity, peak_g, jerk, signals, window_s
    "confirmed_severe":   ("severe",   7.4, 315.0, ["accel_jerk", "gyro", "speed_drop"], 8.0),
    "confirmed_moderate": ("moderate", 4.5, 190.0, ["accel_jerk", "speed_drop"],         13.0),
    "cancel_driver":      ("moderate", 4.1, 175.0, ["accel_jerk", "speed_drop"],         13.0),
    "cancel_deesc":       ("minor",    3.2, 150.0, ["accel_jerk", "gyro"],               13.0),
}


def score_at(elapsed, dur, peak, pf):
    center = pf * dur * 60.0
    width = max(90.0, dur * 60.0 * 0.16)
    return max(0.0, 3.0 + (peak - 3.0) * math.exp(-((elapsed - center) ** 2) / (2 * width ** 2)))


def speed_at(elapsed, dur):
    d = dur * 60.0
    if elapsed < 45 or elapsed > d - 45:
        return 0.0                                  # parked at both ends
    return max(0.0, 11.5 + 4.0 * math.sin(elapsed / 37.0) + random.uniform(-1.0, 1.0))


def level_at(score):
    return "alarm" if score >= 72 else "warn" if score >= 45 else "notice" if score >= 20 else "awake"


def signals_at(score):
    return {
        "ear": round(0.30 - score / 100 * 0.16, 3),
        "perclos": round(min(0.5, score / 100 * 0.45), 3),
        "blink_rate": round(9.0 + score / 100 * 13.0, 1),
        "blink_dur_ms": round(180 + score / 100 * 320),
        "head_nod": round(max(0.0, (score - 50) / 50) * 0.7, 3),
        "yawn": round(max(0.0, (score - 40) / 60) * 0.6, 3),
    }


def fired_at(score):
    if score < 20:
        return []
    if score < 45:
        return ["blink"]
    if score < 72:
        return ["perclos", "blink"]
    return ["perclos", "blink", "head_nod", "yawn"]


def link_at(ride, elapsed, dur):
    if ride["link"] == "online":
        return ("online", 0)
    frac = elapsed / (dur * 60.0)
    if 0.40 <= frac < 0.50:
        return ("offline", int((frac - 0.40) * 300))     # dead zone — buffering
    if 0.50 <= frac < 0.56:
        return ("degraded", max(1, int((0.56 - frac) * 150)))  # reconnected, catching up
    return ("online", 0)


def fatigue_ctx(ride, t0):
    dur = ride["dur"] * 60.0
    lo = max(0.0, t0 - 300.0)
    xs = [lo + k * 10.0 for k in range(int((t0 - lo) / 10.0) + 1)]
    scores = [score_at(x, ride["dur"], ride["peak"], ride["pf"]) for x in xs]
    mx = max(scores) if scores else 0.0
    elev = sum(10.0 for s in scores if s >= 45)
    return {"recent_max_score": round(mx, 1), "was_elevated": mx >= 45,
            "elevated_seconds": elev, "sampled_over_minutes": round((t0 - lo) / 60.0, 1)}


def build_ride(ride, start_ts, session_id):
    """Return a list of (ts, type, payload) for one ride, unsorted."""
    dur_s = ride["dur"] * 60.0
    evs = [(start_ts, E.HELLO, {"pubkey": _PUB, "device": DRIVER,
                                "started_at": round(start_ts, 3), "schema": 1, "naive": False})]

    # heartbeats every 60s
    hb_t = 0.0
    while hb_t <= dur_s:
        sc = score_at(hb_t, ride["dur"], ride["peak"], ride["pf"])
        active = level_at(sc) != "awake" or sc > 8
        duty = "full" if active else "idle"
        lk, pending = link_at(ride, hb_t, ride["dur"])
        evs.append((start_ts + hb_t, E.HEARTBEAT, {
            "uptime_s": round(hb_t, 1), "fps": 14.9 if active else 3.0,
            "target_fps": 15 if active else 3, "duty": duty, "camera_ok": True,
            "sensors_ok": True, "calibrated": hb_t >= 12, "speed_mps": round(speed_at(hb_t, ride["dur"]), 1),
            "link": lk, "pending": pending, "last_ack_age_s": round(random.uniform(0.2, 1.2), 1)}))
        hb_t += 60.0

    # drowsiness: sample every 15s while active, transitions on level change
    prev = "awake"
    dr_t = 0.0
    while dr_t <= dur_s:
        sc = score_at(dr_t, ride["dur"], ride["peak"], ride["pf"])
        lvl = level_at(sc)
        sp = speed_at(dr_t, ride["dur"])
        gated = sp < 2.0
        if lvl != prev:
            evs.append((start_ts + dr_t, E.DROWSINESS, {
                "kind": "transition", "level": lvl, "prev_level": prev, "score": round(sc, 1),
                "signals": signals_at(sc), "fired": fired_at(sc), "agree_count": len(fired_at(sc)),
                "gated": gated, "gate_reason": "not_moving" if gated else None, "calibrated": dr_t >= 12}))
            prev = lvl
        elif lvl != "awake" or sc > 1.0:
            evs.append((start_ts + dr_t, E.DROWSINESS, {
                "kind": "sample", "level": lvl, "prev_level": lvl, "score": round(sc, 1),
                "signals": signals_at(sc), "fired": fired_at(sc), "agree_count": len(fired_at(sc)),
                "gated": gated, "gate_reason": "not_moving" if gated else None, "calibrated": dr_t >= 12}))
        dr_t += 15.0

    # crash lifecycle
    if ride["crash"]:
        sev, peak_g, jerk, sigs, win = CRASH[ride["crash"]]
        t0 = ride["cf"] * dur_s
        iid = f"crash-{session_id}-1"
        loc = {"lat": round(12.90 + random.uniform(-0.05, 0.05), 5),
               "lon": round(77.55 + random.uniform(-0.05, 0.05), 5), "speed_mps": 0.0}
        fc = fatigue_ctx(ride, t0)
        base = {"incident_id": iid, "severity": sev, "peak_g": peak_g, "jerk": jerk,
                "signals_fired": sigs, "location": loc, "window_seconds": win,
                "cancel_window_s": win, "fatigue_context": fc, "ts_detected": round(start_ts + t0, 3)}
        evs.append((start_ts + t0, E.CRASH, {**base, "status": E.UNCONFIRMED}))
        if ride["crash"].startswith("confirmed"):
            evs.append((start_ts + t0 + win, E.CRASH, {**base, "status": E.CONFIRMED, "final_motion": "stopped"}))
        elif ride["crash"] == "cancel_driver":
            evs.append((start_ts + t0 + random.uniform(2, 6), E.CRASH,
                        {**base, "status": E.CANCELLED, "reason": E.REASON_DRIVER}))
        else:  # cancel_deesc
            evs.append((start_ts + t0 + random.uniform(8, 12), E.CRASH,
                        {**base, "status": E.CANCELLED, "reason": E.REASON_DEESCALATED}))
    return evs


_PUB = None  # set in main after key


def main() -> None:
    global _PUB
    _PUB = EventChain(KEY, DRIVER, "s-probe").pubkey_b64

    if "--keep" not in sys.argv:
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute("TRUNCATE events, sessions")
        print("cleared events + sessions")

    ledger = Ledger(DSN, connect_retries=3)
    now = time.time()
    totals = {"events": 0, "rides": 0, "crashes": 0}

    for i, ride in enumerate(RIDES):
        session_id = f"s-seed-{i:02d}"
        start = now - ride["d"] * 86400.0 + (ride["h"] - 12.0) * 3600.0
        chain = EventChain(KEY, DRIVER, session_id)
        evs = build_ride(ride, start, session_id)
        evs.sort(key=lambda x: x[0])                     # emit in time order -> chain matches
        for ts, typ, payload in evs:
            ok, err = ledger.append(chain.make(typ, payload, ts=ts))
            if not ok:
                raise SystemExit(f"seed append failed ({typ} @ {ts}): {err}")
            totals["events"] += 1
        totals["rides"] += 1
        if ride["crash"]:
            totals["crashes"] += 1

    print(f"seeded {totals['rides']} rides · {totals['events']} events · {totals['crashes']} incidents "
          f"for driver '{DRIVER}'")


if __name__ == "__main__":
    main()
