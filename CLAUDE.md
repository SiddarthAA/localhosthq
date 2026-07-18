# CLAUDE.md — ridewme
*(rename freely. This is the living project context — we populate it over time. Read it before every task.)*

## What this is (one line)
An edge driver-safety system that ships a drowsiness **decision engine** (not just a detector) plus sensor-fusion accident detection, aimed at fleet operators. Runs on the laptop now; **Pi-target**, not Pi-running.

## Core principle (the whole point)
Detection is a commodity. The product is the **decision**: calibrated per-driver, corroborated across independent signals, gated by context, and frugal on edge hardware. **The moat is deciding when NOT to fire.** The category's real failure isn't missed yawns — it's false-positive spam that makes drivers cover the camera and rip the box out. Never reduce this system to a single-threshold detector.

## Architecture (broad — data flows one way, video never leaves the edge)
- **sensor-app/** *(exists)* — web app on the driver's phone; streams accelerometer / gyroscope / GPS.
- **cli/** — headless **Python** edge daemon (the "driver box"): camera + MediaPipe + signal extraction + Trust Layer + sensor fusion. Emits **signed events only** over WebSocket. No UI.
- **backend/** — thin **Python (FastAPI)** relay hub: ingests signed events + the sensor stream, stores the tamper-evident audit log, broadcasts to the fleet app. **No CV, no decisions — dumb relay + ledger.**
- **frontend/** — **React + TypeScript (Vite)** fleet-manager dashboard: live driver states, alerts, driver scores, incident cards, signed-log verification. Shows **events, never video**.

Flow: `phone sensors → edge` · `camera → edge` · `edge → (signed events only) → backend → fleet app`.

## The standout layers (keep ALL of them — this is the feature)
0. **Perception** — MediaPipe landmarks. Commodity. Mention in one breath, move on.
1. **Multi-signal extraction** — EAR, PERCLOS (60s window), blink rate + duration, head-nod, yawn. Never trust one cue.
2. **Personal baseline calibration** — first ~12s learns this driver's normal; everything downstream is deviation-from-baseline, not a global constant. This is the honest version of "personalized."
3. **Corroboration + persistence (THE MOAT)** — a fatigue score rises only when multiple signals AGREE and PERSIST over seconds. One signal is a whisper; agreement unlocks a real alarm. **Never flatten this into a threshold.**
4. **Context gating** — suppress alerts unless the vehicle is actually moving (GPS speed). Don't nag a parked driver.
5. **Graduated escalation** — tiered response with hysteresis: calm note → soft chime → escalating alarm that backs off on recovery.
6. **Adaptive duty-cycling (edge flex)** — drop inference fps when the driver is clearly alert, ramp back up when signals stir. "When not to *compute*" — the sibling of "when not to *alert*." Cuts power + heat on a fanless board.
7. **Signed event emission** — tamper-evident Ed25519 events leave the edge; video never does. This is the privacy + court-admissible-evidence pillar.

## Non-negotiables (do NOT drift)
- **Video NEVER leaves the edge.** Only signed events. Privacy + evidence depend on it.
- **No accuracy claims. No bigger model. No model-ensemble.** The win is decision quality + measurable frugality — not out-detecting incumbents we have no data to beat.
- **Never flatten the Trust Layer (Layer 3)** into a plain threshold — that IS the differentiation.
- **Backend stays dumb** — relay + ledger only. All decisions live on the edge (cli/).
- **Pi-TARGET, not Pi-running.** Everything runs on the laptop; frame it as Pi-targeted.
- **Signing + verification stay in Python** (cli + backend) to avoid cross-language canonicalization bugs. The frontend only displays verification status.

## Stack (locked)
- **cli/** — Python · OpenCV (camera) · MediaPipe Tasks FaceLandmarker (native) · PyNaCl (Ed25519) · websockets
- **backend/** — Python · FastAPI · websockets
- **frontend/** — React · TypeScript · Vite · Recharts
- **sensor-app/** *(existing)* — web · DeviceMotion / Geolocation

## Demos that sell it
- **Side-by-side, naive vs. Trust Layer** — naive beeps at every blink; ours stays silent, then one calm escalating alert. *This is the whole pitch in ten seconds.*
- **Adaptive duty-cycle graph** — fps drops when alert, snaps back when drowsy. The "wait, on a Pi?" moment.
- **Context gate toggle** — stopped = silent, moving = engaged.
- **Tamper-test on the signed log** — flip a byte → verification goes red.

## Working notes (populate over time)
- [ ] Port earlier TS reference modules (signals / trust layer / fusion / signed log) into Python under cli/
- [ ] Define the signed-event schema shared by cli ↔ backend
- [ ] Map sensor-app payload → fusion SensorSample shape

---

## sensor-app — how to fetch sensor data + video feed (integration reference)
*Source of truth: `sensor-app/README.md`. This is the consumer view for cli/ (edge) and backend/.*

**Topology.** `iphone-xr` (emitter, Safari/https) → **shawarma** (streaming hub, the `sensor-app` repo runs here) → **your backend** (chutney / anywhere on the tailnet). The phone emits; shawarma re-serves; **cli/ consumes and runs the logic**.

**Host / transport.** `HOST = shawarma.chipmunk-balance.ts.net` (or IP `100.94.92.13`), port **`8000`**. Consumers use plain **`http` / `ws`** over the tailnet — **no TLS needed** (Tailscale is already encrypted). Only the *phone* needs the `https` origin (iOS gates camera/sensors behind a secure context).

**Main recipe — video + synchronized sensors.** Copy the standalone `sensor-app/sensor_client.py` into cli/. `SensorCam.read()` mirrors `cv2.VideoCapture.read()` but also hands you the latest sensor packet:
```python
from sensor_client import SensorCam            # deps: numpy, opencv-python, websocket-client
cam = SensorCam("shawarma.chipmunk-balance.ts.net")   # MJPEG video + sensor WS, auto-reconnect
ok, frame, sensors = cam.read()
#   frame   -> BGR numpy array (H, W, 3), ready for OpenCV / MediaPipe
#   sensors -> newest sensor packet (dict): sensors["gyro"], ["accelG"], ["orient"], ["gps"]
```

**Other access modes.**
- **Video only:** `cv2.VideoCapture("http://shawarma…:8000/stream/video.mjpeg")`.
- **Sensors only (push):** `ws://shawarma…:8000/ws/stream/sensors` — one JSON packet per phone sample (~60 Hz).
- **Sensors only (poll):** `GET http://shawarma…:8000/latest/sensors` → newest packet as JSON.
- **CV results channel** (if logic runs in-process on shawarma): `ws://shawarma…:8000/ws/stream/cv`.

**Key consume endpoints (on `shawarma:8000`).**
| Endpoint | Payload |
|---|---|
| `GET /latest/sensors` | newest sensor packet (JSON) |
| `GET /latest/frame.jpg` | newest raw frame (JPEG) |
| `GET /stream/video.mjpeg` | raw video — OpenCV `VideoCapture` source |
| `WS  /ws/stream/sensors` | live sensor push (JSON text, ~60 Hz) |
| `WS  /ws/stream/frames` | live raw frames push (binary JPEG) |

**Sensor packet shape** (maps to the fusion `SensorSample` — see working note above):
```json
{
  "device": "iphone-xr",
  "t": 1721300000000,        // wall-clock ms (Date.now) — align across devices
  "mono": 12345.6,           // monotonic ms (performance.now) — ordering/rate
  "interval": 0.016,         // seconds between motion samples
  "accel":  {"x": .., "y": .., "z": ..},           // acceleration, gravity removed (m/s²)
  "accelG": {"x": .., "y": .., "z": ..},           // acceleration incl. gravity (m/s²)
  "gyro":   {"alpha": .., "beta": .., "gamma": ..}, // rotation rate (°/s)
  "orient": {"alpha": .., "beta": .., "gamma": .., "compass": ..}, // degrees
  "gps":    {"lat": .., "lon": .., "alt": .., "acc": .., "speed": .., "heading": ..}, // or null
  "recv_t": 1721300000.01    // server receive time (added on ingest)
}
```
> **`gps.speed`** is the signal for **context gating (Layer 4)**. Video is consumed *only on the edge (cli/)* — it never flows onward to backend/frontend.

---

## Setup / conventions
- **Project name:** `ridewme` (working name; the ridewme brief above is the product spec — same system, renamed).
- **Package manager: `uv`** everywhere. Mirror the sensor-app convention:
  `uv venv .venv --python 3.12` then `uv pip install -r requirements.txt`.
- **backend/ + cli/ share ONE uv venv** at the repo root (`.venv/`). Both install their `requirements.txt` into it:
  `uv pip install -r backend/requirements.txt -r cli/requirements.txt` (activate `./.venv`).
- **frontend/** is the default Vite React-TS template — `cd frontend && npm install && npm run dev`.
- **sensor-app/** is already set up and **must not be touched**; consume it per the reference above.

---

## Screenshots live on the remote laptop (`chutney`)

Any reference to a **screenshot** in this project should be fetched from the remote
laptop `chutney`, not from this local machine. When the user mentions a screenshot —
whether they paste a full path, just a filename, or say something like "the latest
screenshot" — resolve it against `chutney` and pull it over before reading it.

### Connection details

- **Host:** `sidd@chutney` (reachable over the user's Tailscale network).
- **Auth:** key-based SSH is already set up (`~/.ssh/id_ed25519`). Non-interactive
  commands work — use `ssh -o BatchMode=yes sidd@chutney '...'`.
- **Screenshots directory:** `/home/sidd/Pictures/Screenshots/` (files are named like
  `Screenshot from YYYY-MM-DD HH-MM-SS.png`).

### How to fetch

1. **User pasted a full path** → fetch that exact path from `chutney`.
2. **User gave just a filename** → prepend `~/Pictures/Screenshots/` on `chutney`.
3. **User said "latest" / "most recent"** → resolve the newest file first:
   ```
   ssh -o BatchMode=yes sidd@chutney 'ls -t ~/Pictures/Screenshots/*.png | head -1'
   ```

Then copy it to a local temp/scratchpad path and `Read` it:
```
scp -o BatchMode=yes "sidd@chutney:<remote-path>" <local-scratchpad>/shot.png
```

### Notes

- Quote remote paths — screenshot filenames contain spaces.
- Prefer the remote `chutney` copy over any local `~/Pictures/Screenshots/` on this
  machine; the local one is not the source of truth.
- If key auth ever breaks, re-install the pubkey with
  `ssh-copy-id -i ~/.ssh/id_ed25519.pub sidd@chutney` (needs the `chutney` password once).
