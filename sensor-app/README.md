# sensor-app

Stream IMU + GPS + video from an iPhone (over Tailscale) into a server that
re-serves everything in formats your own backend can plug into. The phone emits;
**shawarma** is a streaming hub; **your code consumes the streams and runs your
logic on top**.

```
 iphone-xr ──(Safari, https)──► shawarma ──► your backend (chutney / anywhere on the tailnet)
   emitter                       hub          YOUR LOGIC: CV, fusion, control, storage…
```

| Device | Tailscale | Role |
|--------|-----------|------|
| iphone-xr | `iphone-xr.chipmunk-balance.ts.net` | opens the web page, streams sensors + camera |
| shawarma  | `shawarma.chipmunk-balance.ts.net` (`100.94.92.13`) | the hub — this repo runs here |
| chutney   | `chutney.chipmunk-balance.ts.net` (`100.122.226.31`) | your backend / consumer |

> **Consumers use plain `http`/`ws` on port `8000`** straight to the server — the
> Tailscale network is already encrypted, so no TLS needed. Only the **phone**
> needs the `https` origin (iOS gates the camera/sensors behind a secure context).

---

# Integrate into your backend

This is the part you care about: get `frame` + `sensors` into your code and add
your logic. Two ways to place that logic — pick per recipe below.

- **A · Pull from your own service** (recommended when your backend is separate) —
  your process connects to `shawarma:8000` over the tailnet and consumes the
  streams. Nothing on the server changes.
- **B · Run in-process on shawarma** (lowest latency, "server is the source of
  everything") — drop your code into the CV worker; results are re-served on the
  existing endpoints.

Host for every recipe: `HOST = "shawarma.chipmunk-balance.ts.net"` (or the IP `100.94.92.13`).

## Recipe 1 — video + synchronized sensors (the main one)

`sensor_client.py` is **standalone** — copy it into your backend repo. Deps:
`pip install numpy opencv-python websocket-client`.

```python
from sensor_client import SensorCam   # copied into your project

cam = SensorCam("shawarma.chipmunk-balance.ts.net")   # MJPEG video + sensor WS, auto-reconnect
try:
    while True:
        ok, frame, sensors = cam.read()
        if not ok:
            continue
        # ==================== YOUR CORE LOGIC ====================
        # frame   -> BGR numpy array (H, W, 3), ready for OpenCV / a model
        # sensors -> newest sensor packet (dict); see "Sensor packet" below
        #   sensors["gyro"], sensors["accelG"], sensors["orient"], sensors["gps"]
        my_pipeline(frame, sensors)
        # =========================================================
finally:
    cam.release()
```

`read()` mirrors `cv2.VideoCapture.read()` but also hands you the latest sensor
packet alongside each frame, so your logic gets image + motion together.

## Recipe 2 — video only (pure OpenCV, drop-in)

```python
import cv2
cap = cv2.VideoCapture("http://shawarma.chipmunk-balance.ts.net:8000/stream/video.mjpeg")
ok, frame = cap.read()   # frame: BGR numpy array
```

## Recipe 3 — sensors only (live push)

```python
import json, websocket   # pip install websocket-client
ws = websocket.create_connection("ws://shawarma.chipmunk-balance.ts.net:8000/ws/stream/sensors")
while True:
    s = json.loads(ws.recv())   # one packet per phone sample (~60 Hz)
    my_logic(s)
```

Prefer stateless polling? `GET http://shawarma…:8000/latest/sensors` returns the
newest packet as JSON. `GET …/latest/frame.jpg` returns the newest frame.

## Recipe 4 — consume the server's CV results

If you add logic in-process (option B), its output is published on the CV channel:

```python
import json, websocket
ws = websocket.create_connection("ws://shawarma.chipmunk-balance.ts.net:8000/ws/stream/cv")
while True:
    result = json.loads(ws.recv())   # whatever process() returned as metrics
```

## Recipe 5 — any language

Everything is plain HTTP + WebSocket + JPEG/JSON, so any stack works:
- Sensors / CV results: WebSocket `ws://shawarma…:8000/ws/stream/{sensors,cv}` (JSON text)
- Video: MJPEG `http://shawarma…:8000/stream/video.mjpeg`, or poll `…/latest/frame.jpg`
- Latest snapshots: `GET …/latest/{sensors,cv,frame.jpg}`

## Option B — add logic in-process on shawarma

Edit `process(frame, prev_gray)` in `server/cv/pipeline.py`. It gets each frame
as a BGR numpy array and returns `(metrics_dict, annotated_or_None, gray)`:

- add fields to `metrics` → they appear on `/latest/cv` and `/ws/stream/cv`
- return an `annotated` frame (instead of `None`) → your drawing shows up on `/stream/cv.mjpeg`
- default returns `None` → the feed is a clean, unmodified video passthrough

This keeps all compute on the server; every consumer above then reads your
results without touching the phone.

---

# Data reference

## Endpoints (on `shawarma:8000`)

**Consume (server → your backend)**
| Endpoint | Payload |
|---|---|
| `GET /latest/sensors` | newest sensor packet (JSON) |
| `GET /latest/cv` | newest CV result (JSON) |
| `GET /latest/frame.jpg` | newest raw frame (JPEG) |
| `GET /latest/cv_frame.jpg` | newest processed frame (JPEG) |
| `GET /stream/video.mjpeg` | raw video — OpenCV `VideoCapture` source |
| `GET /stream/cv.mjpeg` | processed video (clean passthrough until you add CV) |
| `WS  /ws/stream/sensors` | live sensor push (JSON text) |
| `WS  /ws/stream/cv` | live CV-result push (JSON text) |
| `WS  /ws/stream/frames` | live raw frames push (binary JPEG) |

**Ingest (phone → server)** — you normally don't touch these:
`WS /ws/sensors` (JSON), `WS /ws/video` (binary JPEG).

**View / UI:** `GET /` landing · `GET /emit` phone streamer · `GET /dashboard` viewer.

## Sensor packet

```json
{
  "device": "iphone-xr",
  "t": 1721300000000,        // wall-clock ms (Date.now) — align across devices
  "mono": 12345.6,           // monotonic ms (performance.now) — ordering/rate
  "interval": 0.016,         // seconds between motion samples
  "accel":  {"x": .., "y": .., "z": ..},          // acceleration, gravity removed (m/s²)
  "accelG": {"x": .., "y": .., "z": ..},          // acceleration incl. gravity (m/s²)
  "gyro":   {"alpha": .., "beta": .., "gamma": ..},// rotation rate (°/s)
  "orient": {"alpha": .., "beta": .., "gamma": .., "compass": ..}, // degrees
  "gps":    {"lat": .., "lon": .., "alt": .., "acc": .., "speed": .., "heading": ..}, // or null
  "recv_t": 1721300000.01    // server receive time (added on ingest)
}
```

## CV result (default `process()`)

```json
{ "t": 1721300000.02, "width": 640, "height": 480, "brightness": 128.4, "motion": 3.1 }
```
Fields are whatever `process()` returns — extend it with your own.

---

# Setup (run the hub on shawarma)

1. **Run the server**
   ```bash
   ./run.sh          # builds the uv venv on first run, then serves 0.0.0.0:8000
   ```
2. **Expose HTTPS for the phone** (iOS needs a secure origin for camera/sensors)
   ```bash
   tailscale serve --bg 8000
   tailscale serve status   # https://shawarma.chipmunk-balance.ts.net -> 127.0.0.1:8000
   ```
   If it errors, enable **HTTPS certificates** + **MagicDNS** in the Tailscale
   admin console (DNS tab), then re-run.
3. **Phone (iphone-xr)** → Safari → `https://shawarma.chipmunk-balance.ts.net/emit`
   (note: `https`, **no `:8000`**) → tap **Start streaming**, accept the prompts.
   Unsure of the URL? Open `…ts.net/` and use the landing page links.
4. **Watch it** → open `http://shawarma.chipmunk-balance.ts.net:8000/dashboard`
   in any browser on the tailnet. Live feed + gyro/accel graphs + GPS/compass;
   the page only displays, all compute is on the server.

## Tuning

Emitter capture settings live in `CONFIG` at the top of `web/app.js`:
`maxFps` (send rate cap — actual rate follows the phone camera and backs off under
network pressure), `width` (JPEG width), `quality` (0–1). Bump them once the pipe
is proven. Server-side JPEG re-encode quality (only used when you return an
annotated frame) is in `server/cv/pipeline.py`.
