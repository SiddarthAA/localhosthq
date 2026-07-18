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

Crash fusion: `fusion.py` (≥2-of-3 + cancel countdown). Orchestration: `daemon.py`.
Input sources (phone / replay / synthetic): `sources.py`. Naive baseline: `naive.py`.

## Tests

```bash
VIRTUAL_ENV=../.venv uv pip install -r ../requirements-dev.txt
../.venv/bin/python -m pytest tests
```
