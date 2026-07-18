# CONTRACT.md — ridewme shared contract

The one artifact every process agrees on. **Define this before wiring anything** (design doc's
instruction). Two contracts live here:

1. **The signed-event schema** — what the edge daemon (`cli/`) emits and the backend (`backend/`)
   verifies + stores. This is signature-critical: the canonical byte form is normative.
2. **The backend → fleet-app API** — WebSocket + REST the frontend renders. **Build the frontend
   against §5.** It never sees the daemon, frames, or raw sensors — only what the backend serves.

Schema version: **`v = 1`**. Any breaking change bumps `v` and this doc.

---

## 1. Golden flow (one direction, nothing raw flows up)

```
 phone (sensor-app) ──sensors+video──►  cli/ edge daemon  ──signed events──►  backend/  ──WS/REST──►  frontend/
                                        (all CV + decisions)                  (ledger + relay)        (renders only)
```

- Camera + raw sensors **terminate at the daemon**. Only **signed events** go up.
- Backend makes **zero decisions** — it verifies, appends to the tamper-evident ledger, holds current
  per-driver state, and fans out. If logic touches raw data or makes a judgment, it's a daemon bug.
- Frontend **displays** — including signature-verification status; it never verifies crypto itself.

---

## 2. The signed event (daemon → backend)

Every event is a JSON object with a fixed **envelope** + a type-specific **payload**, then signed.

### 2.1 Envelope (all events)

| field       | type   | notes |
|-------------|--------|-------|
| `v`         | int    | schema version, currently `1` |
| `type`      | string | `hello` \| `heartbeat` \| `drowsiness` \| `crash` |
| `driver_id` | string | stable id for the driver/box (fleet key) |
| `session_id`| string | one daemon run; changes every restart |
| `seq`       | int    | monotonic per `session_id`, starts at `0` (the `hello`) |
| `ts`        | float  | unix epoch seconds (event time), 3-decimal precision |
| `prev_sig`  | string | base64 of the previous event's `sig`; `""` for `seq == 0` |
| `payload`   | object | type-specific, see §2.3 |
| `sig`       | string | base64 Ed25519 signature — see §3 |

`sig` is **not** part of the signed bytes. Everything else is. The chain is covered because `seq`
and `prev_sig` are inside the signed bytes.

### 2.2 Canonical byte form (NORMATIVE — both sides must match exactly)

```
canonical_bytes(event) =
    json.dumps(event_without_sig, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        .encode("utf-8")
```

- `event_without_sig` = the envelope+payload dict with the `sig` key removed.
- Sorted keys, no whitespace, UTF-8. Floats serialized by Python's `repr`/`json` default; `ts` is
  rounded to 3 decimals **before** signing so the value is stable.
- A frozen **golden vector** (fixed key + fixed event → fixed signature) is checked into both
  `cli/tests/` and `backend/tests/`. If either side changes serialization, that test fails. This is
  how we guarantee no cross-implementation drift.

### 2.3 Payloads by type

**`hello`** (`seq == 0`) — registers this session's public key. Backend pins `pubkey` for the
`(driver_id, session_id)` and verifies every later event against it.
```json
{ "pubkey": "<base64 Ed25519 public key>", "device": "iphone-xr / edge-box-1",
  "started_at": 1721300000.000, "schema": 1, "naive": false }
```

**`heartbeat`** — liveness + duty-cycle telemetry (L6 graph) + uplink health (edge resilience).
```json
{ "uptime_s": 42.5, "fps": 14.9, "target_fps": 15, "duty": "full",
  "camera_ok": true, "sensors_ok": true, "calibrated": true, "speed_mps": 12.4,
  "link": "online", "pending": 0, "last_ack_age_s": 0.4 }
```
`duty` ∈ `full | idle`. Emitted every `heartbeat_s` (default 5s).
`link` ∈ `online | degraded | offline` — the daemon's view of its uplink: `degraded` = connected but
draining a backlog after an outage; `offline` = buffering locally. `pending` = un-acked events still in
the edge's durable outbox; `last_ack_age_s` = seconds since the last ack (null if never acked).

**`drowsiness`** — a decision from L1–L5. Emitted on **level transitions** (always) and as a
throttled **sample** (default 1 Hz) whenever `level != awake` or `score > 0`.
```json
{ "kind": "transition",
  "level": "warn", "prev_level": "notice", "score": 58.3,
  "signals": { "ear": 0.19, "perclos": 0.41, "blink_rate": 7.0, "blink_dur_ms": 480,
               "head_nod": 0.22, "yawn": 0.12 },
  "fired": ["eyes", "head_nod"], "agree_count": 2,
  "gated": false, "gate_reason": null,
  "calibrated": true }
```
- `kind` ∈ `transition | sample`.
- `level` ∈ `awake | notice | warn | alarm` (L5, with hysteresis).
- `score` ∈ `0..100` — a **penalty/recovery debt**: `0` = wide awake; eye closure adds penalty (the
  deeper/longer the eyes are shut, the faster it climbs), head-nod/yawn add smaller penalties, and
  keeping the eyes open pays it back toward `0` each second. A normal blink barely moves it.
- `signals` — the current L1 values (nullable if a signal isn't available yet).
- `fired` — which penalties are active now: subset of `["eyes", "head_nod", "yawn"]`; `agree_count = len(fired)`.
- `gated` — L4 suppressed escalation (context gate, **off by default**); `gate_reason` e.g. `"not_moving"`.

**`crash`** — from the sensor-fusion track (Feature 2). One event per lifecycle transition (chained).
```json
{ "incident_id": "crash-<session>-<n>",
  "status": "unconfirmed",
  "severity": "severe",
  "peak_g": 7.5,
  "jerk": 320.0,
  "signals_fired": ["accel_jerk", "gyro", "speed_drop"],
  "location": { "lat": 12.97, "lon": 77.59, "speed_mps": 0.0 },
  "window_seconds": 8.0,
  "cancel_window_s": 8.0,
  "fatigue_context": { "recent_max_score": 78.0, "was_elevated": true,
                       "elevated_seconds": 240.0, "sampled_over_minutes": 5.0 },
  "ts_detected": 1721300000.0,
  "reason": "driver",          // only on cancelled: "driver" | "deescalated_motion"
  "final_motion": "stopped" }  // only on confirmed: "stopped" | "moving"
```
- **Lifecycle** `unconfirmed → confirmed | cancelled` (the internal `candidate` from Layer 1 is
  never emitted). `unconfirmed` = Layer 2 corroboration passed → **fleet manager only**, a human
  window starts. `cancelled` = driver cancelled OR sustained normal driving (`reason`). `confirmed`
  = the window elapsed consistent → **emergency services** (`final_motion`).
- **Who-hears-what (hard rule):** the ONLY path to emergency dispatch is `confirmed`. Unconfirmed
  never leaves the fleet dashboard. "We don't call 112 on a pothole."
- `severity` ∈ `minor | moderate | severe`; severe shortens the window (faster escalation).
- `signals_fired` ⊆ `["accel_jerk", "gyro", "speed_drop"]`; confirms only when **≥ 2 agree**.
- `fatigue_context` (design §5) — the crash's recent drowsiness correlation. `was_elevated:true`
  after a rising fatigue score = a likely **fatigue-caused crash**.

---

## 3. Signing & the tamper-evident chain (§ both sides, Python)

- **Keys:** the daemon generates an Ed25519 keypair on first run. Private key stays on the edge
  (gitignored). Public key is announced in the `hello` event.
- **Sign:** `sig = base64( Ed25519_sign(private_key, canonical_bytes(event)) )`.
- **Chain:** `event[seq].prev_sig == event[seq-1].sig`. `hello` has `prev_sig == ""`.
- **Verify (backend):** for each event, (a) recompute `canonical_bytes`, (b) check `sig` against the
  session's pinned `pubkey`, (c) check `prev_sig` links to the stored previous `sig`, (d) check
  `seq` is the expected next value. Any failure ⇒ the event is rejected/flagged and
  `GET …/ledger/verify` reports a break at that `seq`.
- **Tamper demo:** edit any stored event's bytes in SQLite → `verify` recomputes and the signature
  (or the chain link) no longer matches → API returns `ok:false, broken_at:<seq>` → frontend shows
  the log entry red.

---

## 4. Ingest: daemon → backend (you can ignore this on the frontend)

- **WS `POST-upgrade /ws/ingest`** — the daemon dials in, optionally with `Authorization: Bearer
  <token>` (shared token in config; off by default for local dev).
- Daemon sends `hello` first, then a stream of events (JSON text frames), one event per frame.
- Backend replies with acks: `{ "ack": <seq>, "session_id": "s-abc", "verified": true }` (or
  `verified:false` + `error`). The daemon does not block on acks.
- **Delivery is at-least-once + durable.** The edge persists every event to a local outbox before
  sending and deletes it only on ack; the backend dedups by `(session_id, seq)`. So a crash, dead
  zone, or backend restart loses nothing — un-acked events replay on reconnect. Safety is unaffected
  either way: the alarm fires on the edge, with no network involved.

---

## 5. Backend → fleet app (**BUILD THE FRONTEND AGAINST THIS**)

Base URL `http://<backend-host>:8080`. All JSON. CORS open for local dev.

### 5.1 WebSocket `GET /ws/fleet` — live subscription

On connect the server sends a **snapshot**, then pushes deltas. Message shapes:

```json
{ "kind": "snapshot", "drivers": [ <DriverState>, ... ], "server_ts": 1721300000.0 }
{ "kind": "state",    "driver": <DriverState> }          // a driver's current state changed
{ "kind": "event",    "driver_id": "d1", "verified": true, "event": <SignedEvent> }  // live feed
```

`DriverState`:
```json
{ "driver_id": "d1", "online": true, "session_id": "s-abc",
  "level": "warn", "score": 58.3, "gated": false,
  "duty": "full", "fps": 14.9, "speed_mps": 12.4, "calibrated": true,
  "link": "online", "pending": 0,
  "last_event_ts": 1721300000.0, "updated_at": 1721300000.4,
  "active_incident": <CrashCard | null> }
```

### 5.2 REST

| method | path | returns |
|--------|------|---------|
| `GET` | `/api/health` | `{ "ok": true, "drivers": 1 }` |
| `GET` | `/api/drivers` | `[ <DriverState>, ... ]` |
| `GET` | `/api/drivers/{id}` | `<DriverState>` |
| `GET` | `/api/drivers/{id}/events?limit=100&type=drowsiness` | `[ <SignedEvent>, ... ]` newest-first |
| `GET` | `/api/incidents?limit=50` | `[ <CrashCard>, ... ]` crash incident cards |
| `GET` | `/api/dispatches` | `[ <DispatchRecord>, ... ]` confirmed crashes that fired dispatch |
| `GET` | `/api/drivers/{id}/ledger/verify` | `<VerifyResult>` — powers the tamper demo |
| `GET` | `/api/drivers/{id}/ledger?limit=200` | `[ <SignedEvent>, ... ]` raw chain for the log view |

`CrashCard`:
```json
{ "incident_id": "crash-s-abc-1", "driver_id": "d1", "severity": "severe",
  "status": "confirmed", "peak_g": 7.5, "jerk": 320.0,
  "signals_fired": ["accel_jerk","gyro","speed_drop"],
  "location": { "lat": 12.97, "lon": 77.59 }, "window_seconds": 8.0,
  "fatigue_context": { "was_elevated": true, "recent_max_score": 78.0,
                       "elevated_seconds": 240.0, "sampled_over_minutes": 5.0 },
  "detected_at": 1721300000.0, "resolved_at": 1721300008.0,
  "reason": null, "final_motion": "stopped" }
```
`DispatchRecord` (fired only on `confirmed`):
```json
{ "incident_id": "crash-s-abc-1", "driver_id": "d1", "severity": "severe",
  "location": { "lat": 12.97, "lon": 77.59 }, "dispatched_at": 1721300008.0 }
```
Also pushed live on `/ws/fleet` as `{ "kind": "dispatch", "driver_id": "d1", "incident": <DispatchRecord> }`.

`VerifyResult`:
```json
{ "ok": true, "count": 1234, "broken_at": null, "checked_at": 1721300020.0 }
// tampered: { "ok": false, "count": 1234, "broken_at": 57, "reason": "signature_mismatch" }
```

### 5.3 Frontend notes
- Levels map to your UI states: `awake` (calm/green) · `notice` (info) · `warn` (amber, soft) ·
  `alarm` (red, prominent). `gated:true` = show "monitoring (parked)", never alarm styling.
- `score` is a smooth 0–100 — good for a gauge/sparkline. Drive the duty-cycle demo graph off
  `heartbeat.fps` + `duty`.
- Crash incident cards come from `/api/incidents`; the instant alert is the `crash` event with
  `status:"detected"` on the WS feed. Show the cancel countdown from `cancel_window_s`.
- Verification badge per log row: call `…/ledger/verify`; if `ok:false`, paint rows at/after
  `broken_at` red.

---

## 6. Invariants (repeat, because they're the product)
- Video + raw sensors **never leave the daemon**. Only signed events (§2).
- Backend makes **zero decisions** (§1). Storage/relay/ledger only.
- **Never flatten L3** into a threshold — `score` is a corroborated, persistent integrator.
- No accuracy claims, no bigger model, no ensemble. The win is decision quality + measurable frugality.
- Pi-target, not Pi-running — runs on the laptop, framed as edge-targeted.
