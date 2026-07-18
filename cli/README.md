# cli — ridewme edge daemon ("driver box")

Headless Python edge daemon: camera + MediaPipe + signal extraction + Trust Layer + sensor
fusion. Emits **signed events only** over WebSocket. No UI. All CV and all decisions live here;
video and raw sensors never leave it. See [`../CONTRACT.md`](../CONTRACT.md) for the event schema.

## Run

```bash
../setup.sh                # one-time: shared root .venv + backend/cli deps
./run.sh --sim             # fully offline demo — scripted drowsy + crash (no sensor server)
./run.sh                   # production: phone camera + sensors (needs sensor-app up)
./run.sh --naive           # strawman per-blink detector (side-by-side demo contrast)
./run.sh --replay clip.mp4 # drive frames from a local video file
```

Operational config is in the repo-root `.env` (`SENSOR_HOST`, `BACKEND_HOST`, `DRIVER_ID`, …).
Engine tuning (thresholds, windows, time-constants) is documented in `ridewme/config.py`.
Type `c`+Enter to cancel a pending crash dispatch.

## The decision engine (`ridewme/`)

| layer | file | role |
|-------|------|------|
| L0 | `perception.py` | MediaPipe FaceLandmarker → EAR/MAR/pitch (commodity) |
| L1 | `signals.py` | PERCLOS, blink rate+duration, head-nod, yawn |
| L2 | `calibration.py` | first ~12s learns this driver's baseline |
| L3 | `trust.py` | **the moat** — corroboration + persistence (leaky integrator) |
| L4 | `gating.py` | suppress unless the vehicle is moving (GPS speed) |
| L5 | `escalation.py` + `audio.py` | graduated escalation with hysteresis + in-cabin audio |
| L6 | `dutycycle.py` | drop inference fps when clearly alert |
| L7 | `signing.py` | Ed25519 signed, chained events |

Orchestration: `daemon.py` (two parallel engines, one signed timeline).
Input sources (phone / replay / synthetic): `sources.py`. Naive baseline: `naive.py`.

## Crash engine (Feature 2)

A second engine runs alongside the drowsiness one, sharing motion state (`motion.py` — Seam 1) and
the same signed timeline, failing independently. Funnel: **pre-gate** (was it moving?) → **Layer 1**
accel-spike candidate → **Layer 2** windowed corroboration (`crash.py`: peak + jerk, gyro ≥2 axes,
GPS speed-drop; ≥2 agree) → `crash.unconfirmed` (fleet only) → **Layer 3** severity-modulated human
window + post-event de-escalation + driver cancel → `crash.confirmed`. Emergency dispatch fires
**only** on confirmed (never a pothole). Each crash carries `fatigue_context` (`fatigue.py`) — a
crash after rising fatigue is a fatigue-caused crash (the 1+1=3 payoff). Ring buffer: `ringbuffer.py`.
Demo inject: `x`+Enter. Live status → `FEATURE2_PROGRESS.md`.

## Resilience (offline-first)

Every signed event is written to a **durable local outbox** (`outbox.py`, SQLite/WAL) before it's
sent, and deleted only when the backend acks it. A crash, a dead zone, or a backend restart loses
nothing — un-acked events replay on reconnect (`uplink.py`, at-least-once; the backend dedups by
`(session, seq)`). The heartbeat reports `link` (online / degraded / offline) + `pending` backlog so
the dashboard shows sync status. **Safety never depends on the network** — the alarm fires on the edge.

## Tests

```bash
VIRTUAL_ENV=../.venv uv pip install -r ../requirements-dev.txt
../.venv/bin/python -m pytest tests
```
