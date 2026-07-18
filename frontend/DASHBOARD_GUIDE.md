# DASHBOARD_GUIDE.md — ridewme fleet dashboard (build reference)

How to build the dashboard against the core engine. **`../CONTRACT.md` is the authoritative
spec**; this is the digested, UI-oriented view.

## Scope (READ FIRST)
**Build for ONE fleet manager watching ONE active driver.** No login, no driver list, no
tenant switching yet. The backend API is already fleet-shaped (it returns arrays), but for now:
- there is exactly **one driver** (`driver_id` defaults to `"driver-1"`),
- take **the first element** of `drivers[]` / `/api/drivers` — don't hardcode the id, just assume one,
- render a **single-driver view** (one big driver panel), not a grid of drivers.

Multi-driver, multi-tenant, auth → **later polish**. Don't design those in now; just don't paint
yourself into a corner (keep the driver's data in one object you could later put in a list).

The dashboard **renders decisions only** — it never sees video or raw sensors.

---

## 0. Seeded data — build your graphs off this

The local Postgres is seeded with ~3 weeks of realistic, **cryptographically-signed** history for
`driver-1` (re-seed anytime: `./.venv/bin/python database/seed.py`, or `--keep` to add without clearing):
- **17 rides** (sessions) over the last ~21 days · **2,721 events** · **5 crash incidents**
- crash mix: **2 confirmed** (1 severe → dispatch, 1 moderate) · **3 cancelled** (2 driver take-backs,
  1 de-escalation) — several preceded by elevated fatigue (`fatigue_context.was_elevated`)
- drowsiness arcs (calm → warn/alarm → recover), duty-cycle heartbeats, a couple of rides with
  connectivity blips (`link: offline/degraded`, `pending>0`)
- `/api/drivers/driver-1/ledger/verify` → **`ok:true, count:2721`** (the tamper demo works on the seed)

### ⚠ History vs live (read this before you wire anything)
- **Graphs / history** come from the **Postgres-backed REST endpoints**, which serve the SEED with
  **no daemon running**: `/api/drivers/driver-1/events`, `/api/incidents`,
  `/api/drivers/driver-1/ledger`, `/ledger/verify`. **Build ALL your charts against these.**
- **Live current-state** (`/api/drivers`, `/ws/fleet`) is in-memory and only populated by a **running
  daemon** — it is **empty until you run `./cli/run.sh --sim`**. Don't expect `/api/drivers` to show
  the seeded driver without a daemon.
- So the mental model: **charts = seed (REST) · live driver tile = a running daemon (WS)**. The
  `driver_id` is `"driver-1"` (hardcode it for the history queries; there's exactly one driver).

### Query recipes → graphs
| Graph | Endpoint → field |
|---|---|
| **Fatigue score timeline** (overall / per ride) | `…/events?type=drowsiness&limit=3000` → `payload.score` vs `ts`, color by `payload.level`; group by `session_id` for per-ride |
| **Rides over time** (rides/day) | `…/events?type=hello` → one per ride; bucket `ts` by day |
| **Level distribution** (awake/notice/warn/alarm) | `type=drowsiness` → count/duration by `payload.level` |
| **Signals fired frequency** | `type=drowsiness` → tally `payload.fired` (perclos/blink/head_nod/yawn) |
| **Duty-cycle / fps · speed · link** | `type=heartbeat` → `payload.fps`+`duty`, `speed_mps`, `link`/`pending` |
| **Incidents** (timeline / outcome donut / severity bars / map) | `/api/incidents` → `severity`, `status`, `reason`, `location`, `detected_at`/`resolved_at` |
| **Fatigue → crash correlation** | each incident's `fatigue_context.was_elevated` / `recent_max_score` → scatter or badge |
| **Signed log + verify badge** | `…/ledger?limit=200` (rows) + `…/ledger/verify` (green/red) |

**KPI headline numbers:** total rides · drowsiness alerts (warn+alarm transitions) · crashes ·
confirmed dispatches · take-backs (cancelled) · avg/max fatigue per ride.

---

## 1. Connect

Base: `http://<backend>:8080` (dev: `http://127.0.0.1:8080`). CORS is open for local dev.

**WebSocket `ws://<backend>:8080/ws/fleet`** — subscribe once; get a snapshot, then live deltas:
```jsonc
{ "kind":"snapshot", "drivers":[DriverState,…], "server_ts":… }   // on connect — take drivers[0]
{ "kind":"state",    "driver": DriverState }                      // the driver's state changed
{ "kind":"event",    "driver_id", "verified":true, "event": SignedEvent }  // every signed event
{ "kind":"dispatch", "driver_id", "incident": DispatchRecord }    // ONLY on crash.confirmed
```
Keep the socket open the whole session; it auto-reconnects on the server side of things, but you
should reconnect on close too. Messages are tiny (≤~1/sec) — no polling needed.

**REST** (for history / one-shot reads):

| path | returns |
|---|---|
| `GET /api/health` | `{ ok, drivers, subscribers }` |
| `GET /api/drivers` | `[DriverState]` — take `[0]` |
| `GET /api/drivers/{id}` | `DriverState` |
| `GET /api/drivers/{id}/events?type=&limit=` | `[SignedEvent]` newest-first (`type` optional: `drowsiness`/`crash`/`heartbeat`) |
| `GET /api/incidents?limit=50` | `[CrashCard]` |
| `GET /api/dispatches` | `[DispatchRecord]` (confirmed crashes only) |
| `GET /api/drivers/{id}/ledger/verify` | `VerifyResult` — the tamper demo |
| `GET /api/drivers/{id}/ledger?limit=200` | `[SignedEvent]` raw signed chain for a log view |

**Rule of thumb:** WS drives the live panel + event feed; REST drives history, the incident list,
and the verify badge.

---

## 2. `DriverState` — the whole dashboard (one object)

```jsonc
{ "driver_id":"driver-1", "online":true, "session_id":"s-…",
  "level":"warn", "score":58.3, "gated":false,          // drowsiness
  "duty":"full", "fps":14.9, "speed_mps":12.4, "calibrated":true,
  "link":"online", "pending":0,                         // connectivity
  "last_event_ts":…, "updated_at":…,
  "active_incident": CrashCard | null }                 // live crash (null when none)
```
- `online` = backend-computed (no event for ~15 s → `false`). `link` = the edge's own view of its uplink.
- This single object is enough for the whole driver panel: fatigue gauge, connection dot, speed,
  calibration state, and the active crash card.

---

## 3. Drowsiness → visuals

**`drowsiness` event** — emitted on **every level change** and a throttled **~1 Hz sample** while not calm:
```jsonc
{ "kind":"transition|sample", "level":"warn", "prev_level":"notice", "score":58.3,
  "signals": { "ear":0.19, "perclos":0.41, "blink_rate":7.0, "blink_dur_ms":480,
               "head_nod":0.22, "yawn":0.12 },
  "fired":["perclos","blink"], "agree_count":2, "gated":false, "gate_reason":null, "calibrated":true }
```

| field | range | visual |
|---|---|---|
| `score` | **0–100**, smooth | the **fatigue gauge** + a live sparkline (the star of the show) |
| `level` | `awake·notice·warn·alarm` | state color: green · info/blue · **amber** · **red** |
| `signals.perclos` | 0–1 (fraction eyes-closed, 60 s window) | signal bar / % |
| `signals.head_nod`, `signals.yawn` | 0–1 (danger) | signal bars |
| `signals.ear` | ~0.30 open, ~0.10 closed | small raw readout |
| `signals.blink_dur_ms` | ~200 normal, **>400 = slow/drowsy** | raw readout |
| `signals.blink_rate` | blinks/min | raw readout |
| `fired` / `agree_count` | subset of `perclos·blink·head_nod·yawn` / 0–4 | **"N signals agree"** chips lighting up |
| `gated` | bool | true → show **"monitoring (parked)"**, never alarm styling |
| `calibrated` | bool | false for the first ~12 s → "learning this driver's baseline…" |

**Gauge zones (match the engine):** level rises at **score 20 / 45 / 72** (notice/warn/alarm) and
falls back with hysteresis at **12 / 38 / 62** — so the score can sit in a band without flipping
levels; don't make your gauge flicker at the edges either.

**The story to tell on screen (this is the product):** a lone signal is a *whisper* — `agree_count:1`
keeps the score low. The score only climbs into `warn/alarm` when **multiple signals agree and
persist over seconds**. Animating `fired` chips lighting up one-by-one as the gauge climbs *is* the
"Trust Layer" moat, visually.

---

## 4. Duty-cycle graph (the "wait, on a Pi?" moment)

From **`heartbeat`** (every 5 s):
```jsonc
{ "uptime_s":42.5, "fps":14.9, "target_fps":15, "duty":"full",
  "camera_ok":true, "sensors_ok":true, "calibrated":true, "speed_mps":12.4,
  "link":"online", "pending":0, "last_ack_age_s":0.4 }
```
Plot **`fps`** over time, shaded by `duty`: it holds **~15 fps** when the driver is alert, drops to
**~3 fps** (`duty:"idle"`) after ~5 s of quiet, and snaps back the instant anything stirs. Tiny
graph, big "it's frugal on edge hardware" point.

---

## 5. Crash → incident card + countdown + dispatch

**`crash` event** — lifecycle **`unconfirmed → confirmed | cancelled`** (the internal Layer-1
`candidate` is never emitted):
```jsonc
{ "incident_id":"crash-s-…-1", "status":"unconfirmed", "severity":"severe",
  "peak_g":7.5, "jerk":320.0, "signals_fired":["accel_jerk","gyro","speed_drop"],
  "location":{"lat":12.97,"lon":77.59,"speed_mps":0.0},
  "window_seconds":8.0, "cancel_window_s":8.0,
  "fatigue_context":{…}, "ts_detected":…,
  "reason":"driver",          // cancelled only: "driver" | "deescalated_motion"
  "final_motion":"stopped" }  // confirmed only: "stopped" | "moving"
```

Card lifecycle in the UI (also available as `DriverState.active_incident` + `/api/incidents`):
1. **`unconfirmed`** → card appears **amber** with a live countdown from `cancel_window_s`
   (8 s severe, ~13 s otherwise). Show `severity`, `peak_g`, `jerk`, `signals_fired` chips, a map pin
   from `location`. **This state reaches the fleet dashboard ONLY** — nobody external is contacted.
2. **`cancelled`** → clear/grey the card; show `reason` ("driver cancelled" vs "resumed normal driving").
3. **`confirmed`** → card flips **red / dispatched**; show `final_motion`. A **`{kind:"dispatch"}`**
   WS message arrives → render "🚑 dispatched → responder @ lat,lng". `/api/dispatches` is the audit list.

- **Severity bands** (peak Δg): `minor <3.5 · moderate 3.5–6 · severe >6`. Severe → **shorter**
  window. Always read the countdown from `window_seconds` / `cancel_window_s`, never a hardcoded value.
- **HARD RULE (encode it):** unconfirmed = fleet-only. Emergency dispatch is shown **only** on
  `confirmed`. Never render "112 / responder called" on an unconfirmed card. "We don't call 112 on a pothole."

---

## 6. Correlation — the headline (`fatigue_context` on every crash)

```jsonc
"fatigue_context": { "recent_max_score":78.0, "was_elevated":true,
                     "elevated_seconds":240.0, "sampled_over_minutes":5.0 }
```
When `was_elevated:true`, badge the crash card **"⚠ elevated fatigue preceding crash"** and show
`elevated_seconds` ("drowsy for ~4 min, then crashed"). This is the two-engines-one-brainstem
insight — a signed correlation no standalone product can produce. Make it prominent.

---

## 7. Signed ledger, tamper demo, connection status

- **Verification badge:** `GET /api/drivers/{id}/ledger/verify` → `{ ok, count, broken_at, reason? }`.
  Green when `ok:true`. **Tamper demo:** editing a stored row → `ok:false, broken_at:57` → paint the
  log rows at/after `broken_at` red. `/api/drivers/{id}/ledger` returns the raw chain
  (`seq`, `type`, `ts`, `sig`, `prev_sig`, `payload`) for a scrolling log view.
- **Connection status:** `link` ∈ `online·degraded·offline` + `pending` backlog.
  - `online:false` (backend) or `link:"offline"` → "offline — buffering on the edge, last synced N s ago"
  - `link:"degraded"` + `pending>0` → "syncing N events…"
  - `link:"online"` → live dot green. (This is the resilience story: pull the network, nothing is lost.)

---

## 8. The demos this dashboard should nail

| Demo | Data that drives it |
|---|---|
| **Naive vs Trust** | daemon `--naive` spams `alarm` transitions every blink; normal daemon stays calm then one graduated climb — same `drowsiness` feed, opposite behavior |
| **Duty-cycle graph** | `heartbeat.fps` + `duty` over time |
| **Context-gate toggle** | `drowsiness.gated` flips with `speed_mps` (parked = gated/silent) |
| **Tamper test** | `/ledger/verify` flips `ok:true → false` |
| **Fatigue → crash** | `crash.fatigue_context.was_elevated` badge |

---

## 9. Enums / ranges / cadences (quick reference)

- **event.type**: `hello · heartbeat · drowsiness · crash`
- **level**: `awake · notice · warn · alarm` — score 0–100; up 20/45/72, down 12/38/62
- **duty**: `full` (~15 fps) · `idle` (~3 fps) · **link**: `online · degraded · offline`
- **crash.status**: `unconfirmed · confirmed · cancelled` · **severity**: `minor · moderate · severe` (3.5 / 6 g)
- **signals_fired**: `accel_jerk · gyro · speed_drop` (≥2 to confirm) · **reason**: `driver · deescalated_motion` · **final_motion**: `stopped · moving`
- **cadence**: heartbeat 5 s · drowsiness sample ~1 Hz (when active) + every transition · crash window 8–13 s
- **ports**: backend **8080** · sensor-app **8000** (reserved) · frontend (Vite) **5173**

---

## 10. Suggested single-driver layout (not prescriptive)
- **Top bar:** driver name + `online`/`link` dot + `speed_mps` + `calibrated` state.
- **Hero:** fatigue **score gauge** (color by `level`) + live sparkline.
- **Signals row:** four bars (`perclos`, `blink`, `head_nod`, `yawn`) with `fired` chips + `agree_count`.
- **Duty strip:** `fps`/`duty` mini-graph.
- **Crash card:** appears on `active_incident` — severity, countdown, map pin, dispatch state, fatigue badge.
- **Ledger panel:** recent signed events + a green/red **verify** badge (tamper demo).

Keep all of it bound to the single driver object; wrapping it in a list for multi-driver is a later,
cheap refactor.
