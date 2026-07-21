# ridewme

An edge driver-safety system: a drowsiness **decision engine** (not just a detector) plus
sensor-fusion crash detection. Video never leaves the edge — only **Ed25519-signed events**
travel to the fleet console.

> **The point:** detection is a commodity. The product is the *decision* — calibrated per
> driver, corroborated across independent signals, and disciplined about **when *not* to fire.**

---

## Table of contents

1. [What runs where](#1-what-runs-where)
2. [Prerequisites](#2-prerequisites)
3. [First-time setup on a new device](#3-first-time-setup-on-a-new-device)
4. [Running it — the 5 pieces](#4-running-it--the-5-pieces)
5. [Running across multiple devices](#5-running-across-multiple-devices)
6. [Configuration reference](#6-configuration-reference)
7. [CLI flags & keyboard controls](#7-cli-flags--keyboard-controls)
8. [The demo script](#8-the-demo-script)
9. [Troubleshooting](#9-troubleshooting)
10. [Tests](#10-tests)

---

## 1. What runs where

| # | Piece | Folder | Port | What it does |
|---|---|---|---|---|
| 1 | **Postgres** | `database/` | `5432` | Tamper-evident signed-event ledger (Docker) |
| 2 | **Collector / backend** | `backend/` | `8080` | Dumb relay + ledger. Ingests signed events, broadcasts to the dashboard |
| 3 | **Fleet dashboard** | `frontend/` | `5177` | React console — live driver state, alerts, charts, ledger verify |
| 4 | **sensor-app** | `sensor-app/` | `8000` | Phone → hub. Streams camera (MJPEG) + accel/gyro/GPS. **Consume only — don't edit** |
| 5 | **Edge daemon** | `cli/` | `8090` (viz) | The "driver box": camera + MediaPipe + decision engine + crash fusion |

**Data flow**

```
phone ──(camera + sensors)──> sensor-app :8000
                                   │
                                   ▼
                          cli/ edge daemon  ── signed events ──> backend :8080 ──> Postgres :5432
                        (all decisions here)                          │
                                                                      ▼
                                                            frontend :5177 (dashboard)
```

Video and raw sensors stop at the edge daemon. Only signed decisions go onward.

---

## 2. Prerequisites

Install these on the machine that will run the stack:

| Tool | Why | Check |
|---|---|---|
| **git** | clone the repo | `git --version` |
| **uv** | Python env + deps (Python **3.12**) | `uv --version` |
| **Node.js 18+ & npm** | the dashboard | `node -v && npm -v` |
| **Docker + Compose** | Postgres ledger | `docker compose version` |
| **Tailscale** *(optional)* | phone → hub over a private network + HTTPS | `tailscale status` |

Install `uv` if missing:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **iOS note:** the phone needs an **HTTPS** origin to grant camera/motion permissions.
> Tailscale Serve (below) provides that. Plain `http://…:8000` will *not* work on iPhone.

---

## 3. First-time setup on a new device

```bash
# 1 — clone
git clone git@github.com:SiddarthAA/localhosthq.git ridewme
cd ridewme

# 2 — environment file (gitignored; read by BOTH backend/ and cli/)
cp .env.example .env
#    then edit .env — at minimum set SENSOR_HOST (see §5/§6)

# 3 — shared Python venv for backend + cli (uv, Python 3.12)
./setup.sh
#    optional: test tooling
VIRTUAL_ENV=.venv uv pip install -r requirements-dev.txt

# 4 — dashboard deps
cd frontend && npm install && cd ..

# 5 — Postgres (schema in database/init/ is auto-applied on first boot)
cd database && docker compose up -d && cd ..
docker compose -f database/docker-compose.yml ps      # should be "healthy"

# 6 — (optional but recommended) seed ~3 weeks of signed history so the
#     charts/KPIs aren't empty on first load
./.venv/bin/python database/seed.py
```

**What `./setup.sh` does:** creates `.venv/` with `uv venv --python 3.12`, then installs
`backend/requirements.txt` + `cli/requirements.txt` into that **one shared venv** (backend
and cli deliberately share it).

**First daemon run** downloads the MediaPipe FaceLandmarker model (~a few MB) to
`cli/models/face_landmarker.task` automatically. No action needed, just don't kill it mid-download.

---

## 4. Running it — the 5 pieces

Open a terminal per piece. **Order matters** (DB → collector → dashboard → phone → daemon).

### 4.1 Postgres (ledger)
```bash
cd database && docker compose up -d
```
Stays up between runs. `docker compose down` stops it (keeps data); `down -v` wipes the ledger.

### 4.2 Collector / backend → `:8080`
```bash
./backend/run.sh
```
Expect: `[backend] serving http://0.0.0.0:8080  db=postgres://…`
Sanity check: `curl http://127.0.0.1:8080/api/health` → `{"ok":true,…}`

### 4.3 Fleet dashboard → `:5177`
```bash
cd frontend && npm run dev
```
Open **`http://<host>:5177`** → log in with:

```
email:    admin@ridewme.in
password: password
```

Top-right you get a **mode toggle** and a **sound toggle**:

| Mode | Behaviour |
|---|---|
| **Live** | Full `/ws/fleet` stream — telemetry tile updates continuously |
| **Alerts** | Same socket, but the tile only updates on alerts (drowsy→alarm, crash, dispatch) |
| **Seeded** | Offline in-browser demo — no backend needed, includes "Simulate drowsiness"/"Trigger crash" buttons |

> Click anywhere once after loading — browsers block audio until a user gesture, and that
> arms the alert chimes.

### 4.4 sensor-app (phone hub) → `:8000`
```bash
cd sensor-app
./run.sh                       # first run builds its own venv; serves 0.0.0.0:8000
tailscale serve --bg 8000      # HTTPS origin (required for iPhone camera/sensors)
```
On the **phone**, open the HTTPS URL Tailscale prints, go to the emitter page, grant
camera + motion permission, and hit the **toggle** to start streaming.

Verify the hub is receiving:
```bash
curl http://<sensor-host>:8000/latest/sensors      # newest sensor packet
```

### 4.5 Edge daemon (the driver box) → viz on `:8090`
```bash
./cli/run.sh --panel --viz
```
It sets everything up, then **waits**:

```
Ready when you are — start the sensor-app, aim the camera, open the dashboard,
then press Enter to begin the ride  (Ctrl-C to abort)…
```

Frame the camera, then hit **Enter**. You get:
- the **driver POV panel** in that terminal (`--panel`)
- the **engine X-ray** at **`http://<host>:8090`** (`--viz`) — annotated video, live scores,
  accel/gyro graphs, low-light indicator, and a **`◨ sound`** button

**No phone? Run fully offline:**
```bash
./cli/run.sh --sim --panel        # scripted drowsy + crash scenario, no sensor-app needed
```

---

## 5. Running across multiple devices

Nothing is hard-wired to one machine — every hop is an env var. Typical split: the **phone**
emits, a **server** (e.g. `shawarma`) runs the stack, and you **SSH in from a laptop**.

### 5.1 The three addresses you must set

| What | Where | Setting |
|---|---|---|
| Daemon → sensor-app | root `.env` | `SENSOR_HOST=<host running sensor-app>` (port `8000`) |
| Daemon → collector | root `.env` | `BACKEND_HOST=<host running backend>` (port `8080`) |
| Dashboard → collector | auto | Derived from the page's own host on `:8080`. Override in `frontend/.env` with `VITE_BACKEND_URL` |

So opening the dashboard at `http://myserver:5177` automatically talks to `http://myserver:8080`.
Backend CORS defaults to `*`, so cross-host works out of the box.

### 5.2 ⚠️ Vite host allow-list (the #1 gotcha on a new machine)

`frontend/vite.config.ts` pins:
```ts
server: { host: true, port: 5177, allowedHosts: ['shawarma', '.chipmunk-balance.ts.net'] }
```
On a machine with a **different hostname**, Vite will refuse the request. Either browse via
`http://localhost:5177` / the raw IP, or add your hostname to `allowedHosts`.

### 5.3 Running everything on one new laptop

```bash
# .env
SENSOR_HOST=127.0.0.1     # if sensor-app runs locally too
BACKEND_HOST=127.0.0.1
DATABASE_URL=postgresql://ridewme:ridewme@127.0.0.1:5432/ridewme
```
The phone still needs to reach the sensor-app over HTTPS — use `tailscale serve --bg 8000`.

### 5.4 SSH'ing in from another machine (audio caveat)

If the daemon runs on a server but you're sitting at a laptop, **the CLI's own alarm plays on
the server**, not on your laptop — SSH doesn't forward audio. To hear alerts where you're sitting:

- open the **viz page** `http://<server>:8090` in **your local browser** and click **`◨ sound`**, and/or
- open the **dashboard** locally and enable its **sound toggle**.

### 5.5 Running more than one daemon

The durable outbox is a single SQLite file. Give each extra daemon its own:
```bash
OUTBOX_PATH=/tmp/driver2.db ./cli/run.sh --sim --driver-id driver-2
```

---

## 6. Configuration reference

### Root `.env` (read by **backend/** and **cli/**)

| Var | Default | Meaning |
|---|---|---|
| `SENSOR_HOST` | `shawarma.chipmunk-balance.ts.net` | Host running sensor-app |
| `SENSOR_PORT` | `8000` | **Reserved** — never bind this yourself |
| `BACKEND_HOST` | `127.0.0.1` | Where the daemon reaches the collector |
| `BACKEND_PORT` | `8080` | Collector HTTP + WS |
| `DRIVER_ID` | `driver-1` | Driver identity (`session_id` is per-run) |
| `INGEST_TOKEN` | *(empty)* | Optional bearer token on `/ws/ingest`; empty = no auth |
| `CAMERA_SOURCE` | `phone` | `phone` \| `replay` |
| `REPLAY_VIDEO` | *(empty)* | Video file when `CAMERA_SOURCE=replay` |
| `AUDIO_ENABLED` | `true` | Local in-cabin escalation audio |
| `NAIVE_MODE` | `false` | Strawman per-blink detector (demo contrast) |
| `CONTEXT_GATE` | `false` | L4 "don't nag a parked driver" — off so it always tracks |
| `DATABASE_URL` | `postgresql://ridewme:ridewme@127.0.0.1:5432/ridewme` | Ledger DSN |
| `CORS_ORIGINS` | `*` | Origins the fleet app may call from |
| `OUTBOX_PATH` | `cli/outbox.db` | Durable store-and-forward file (override per daemon) |

> `.env.example` lists `FRONTEND_PORT=5173` for the port map, but the dev server actually
> runs on **`5177`** (set in `frontend/vite.config.ts`).

### `frontend/.env` (optional — copy from `frontend/.env.example`)

| Var | Default | Meaning |
|---|---|---|
| `VITE_BACKEND_URL` | *page host* `:8080` | Collector base URL |
| `VITE_DRIVER_ID` | `driver-1` | Driver the console focuses on |
| `VITE_DRIVER_NAME` | `Driver 1` | Display name |

---

## 7. CLI flags & keyboard controls

```bash
./cli/run.sh [flags]
```

| Flag | Effect |
|---|---|
| `--panel` | In-cabin **driver POV** panel (needs a TTY) |
| `--viz` | Serve the **engine X-ray** visualizer (annotated video + metrics) |
| `--viz-port N` | Visualizer port (default `8090`) |
| `--sim` | Fully offline: scripted drowsy + crash, **no sensor-app needed** |
| `--replay FILE` | Use a local video file instead of the phone camera |
| `--naive` | Strawman per-blink detector — the side-by-side contrast demo |
| `--driver-id ID` | Override `DRIVER_ID` |
| `--backend-host H` | Override `BACKEND_HOST` |
| `--no-audio` | Disable local audio |
| `--no-wait` | Skip the "press Enter to start the ride" prompt (for scripts) |
| `--crash-at S` | `--sim` only: inject the crash at S seconds |

**While running** (type + Enter in the daemon terminal):

| Key | Action |
|---|---|
| `x` | **Force a crash** — guaranteed confirm → dispatch. Use this if a shake won't cooperate |
| `c` | **Driver cancel** during the 10-second crash countdown |

---

## 8. The demo script

1. **Live decision** — dashboard in *Live* mode: fatigue gauge, PERCLOS/blink/head-nod/yawn
   bars, fps and duty all moving in real time.
2. **The moat** — blink normally: *nothing*. Now hold your eyes shut ~1.5 s → score climbs →
   **ALARM**, chime fires, Alerts panel logs it, the viz video border reddens.
3. **Naive vs Trust** — *Seeded* mode → **Naive mode** button: it beeps at every blink.
   Toggle off → silence. The whole pitch in ten seconds.
4. **Adaptive duty-cycle** — the fps chart: ~15 fps alert → ~3 fps calm → snaps back.
5. **Crash → dispatch** — shake **and twist** the phone (accel **and** gyro must agree), or
   type `x`⏎. Driver box shows **IMPACT DETECTED · 10 s countdown**; press `c` to cancel, or
   let it run → **CONFIRMED** → *Fleet manager notified · contacting Apollo Spectra Koramangala*,
   and the dashboard pops the **"Pinging nearest hospital"** card + chime.
6. **Fatigue → crash correlation** — the confirmed card shows *"Elevated fatigue preceding crash."*
7. **Tamper-evident ledger** — bottom panel → **Tamper a row** → the Ed25519 verify badge flips
   **red**. Restore → green.
8. **Alerts-only mode** — flip to *Alerts*: telemetry pauses, only incidents surface.

---

## 9. Troubleshooting

**Port already in use.** Find and free it:
```bash
ss -ltnp | grep -E ':8080|:5177|:8090'
kill -9 <pid>
```
Leave Postgres (`:5432`) running — it's just the DB.

**Crash won't trigger when I shake.** It needs **accel *and* gyro** to agree — a pure straight-line
shake may not rotate the phone. **Shake *and* twist.** Watch the daemon terminal for
`[CRASH] unconfirmed …`. If you need a guaranteed fire, type `x`⏎. (Historic gotcha: the daemon
now timestamps sensor ingest on the server clock — mixing it with the phone's clock used to gate
the engine permanently.)

**Dashboard shows "offline" / empty charts.** The collector isn't reachable. Check
`curl http://<host>:8080/api/health`, confirm `VITE_BACKEND_URL` (or that you're browsing the
same host), and remember the Vite `allowedHosts` gotcha (§5.2).

**Live tile is blank but charts have data.** Normal — charts come from the Postgres ledger,
the live tile needs a **connected daemon**. Start the daemon.

**No video / MediaPipe errors.** Confirm the sensor-app is up (`curl http://<sensor-host>:8000/latest/frame.jpg`),
and that the phone's stream toggle is ON.

**Video capped ~17 fps.** That's the phone camera, not the pipeline — cameras drop frame rate in
low light to lengthen exposure. More light → higher fps. 15–20 fps is plenty for the engine.

**Dark cabin.** The engine auto-brightens dark frames before landmarking; the viz shows a
**`◐ low light · boosting`** chip when it kicks in.

**No sound.** Browsers block autoplay — click once on the page, and use the viz **`◨ sound`**
button / the dashboard sound toggle. Remote over SSH? See §5.4.

**Fresh start.** Restart the collector to clear in-memory live state (the ledger persists).
Wipe the ledger entirely with `cd database && docker compose down -v && docker compose up -d`,
then re-run `database/seed.py`.

---

## 10. Tests

```bash
./.venv/bin/python -m pytest cli/tests backend/tests -q     # engine + ledger
cd frontend && npx tsc -b && npm run build                  # dashboard type-check + bundle
```

The engine tests are the product claim in executable form: a normal blink must **not** alarm,
a pothole must **not** confirm a crash, the driver can always cancel, and the signed chain must
verify byte-for-byte.
