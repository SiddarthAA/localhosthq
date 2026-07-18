# Feature 2 — Crash Detection & Sensor Fusion · live progress

Building everything **except** frontend integration. Updated as each piece lands.
Legend: ✅ done + tested · 🚧 in progress · ⬜ not started

## Build order (design §12)
- ✅ **1. Sensor ingest + ring buffer** — `ringbuffer.py` (source-timestamped, evicts on age); tested
- ✅ **1b. VehicleMotion (Seam 1)** — `motion.py` (single producer, fail-safe = moving); tested
- ✅ **2. Pre-gate + Layer 1 trigger** — `crash.py` (pre-gate + accel-spike candidate); tests pending
- ✅ **3. Layer 2 corroboration** — `crash.py` (peak+jerk, gyro ≥2 axes, speed-drop; ≥2 agree → unconfirmed); tests pending
- ✅ **4. Layer 3 behavioral confirmation** — `crash.py` (severity-modulated window + de-escalation + cancel); tests pending
- ✅ **5. Wire Seam 1** — drowsiness gate reads `MotionState.moving_for_gate` (fail-safe = moving); tested
- ✅ **6. Wire Seam 2/3** — both engines → one signed chain + durable outbox + one WS (daemon `_emit`)
- ✅ **7. Correlation** — `fatigue.py` FatigueHistory + `fatigue_context` on crash payload; tested
- ✅ **8. Backend** — relay unconfirmed/cancelled to fleet; `dispatch.py` fires ONLY on `confirmed`; ledger all
- ⬜ **9. Frontend** — OUT OF SCOPE (parallel agent)
- ✅ **10. Driver-cancel input + "simulate impact"** — CLI `c` cancels, `x` injects impact

## Cross-cutting
- ✅ Event schema + CONTRACT.md updated (crash lifecycle, payloads, `fatigue_context`, dispatch, `/api/dispatches`)
- ✅ Tunables (design §11) centralized in `config.py`
- ✅ Aggressive tests: ring buffer, motion fail-safe, pre-gate, L1, L2 (jerk/gyro-2axis/speed-drop/severity), L3 (window/de-escalation/cancel), correlation, backend dispatch — **48/48 pass**
- ✅ End-to-end synthetic smoke — daemon(--sim) → backend → ledger: `unconfirmed → confirmed`,
  `/api/dispatches` fired only on confirmed, `verify ok:true`, backend logged `[DISPATCH]`

## Status: Feature 2 core COMPLETE (frontend integration out of scope)
All 10 build-order items done; 48/48 tests pass; crash flow verified end-to-end through Postgres.
Not committed — awaiting review.

## Invariants held (design §1, §8)
- Emergency services contacted **only** on `crash.confirmed`; unconfirmed → fleet only
- No trained ML on the confirm path — the fusion heuristic is the intelligence
- Backend stays dumb: no crash logic, no timers — reacts to terminal events
- Two engines fail independently; safety never depends on the network (alarm is on-edge)

## Notes
- Envelope kept stable (golden vector + frontend contract intact); `type` discriminates engine, crash
  lifecycle in `payload.status` (`unconfirmed`/`confirmed`/`cancelled`).
