"""FastAPI relay hub — implements CONTRACT §4 (ingest) and §5 (fleet API).

Zero decisions. On each ingested event: verify + append to the ledger, update
per-driver state, broadcast to fleet subscribers, ack the daemon. REST serves
snapshots, history, incident cards, and ledger verification (the tamper demo).
"""

from __future__ import annotations

import json
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Config, load_config
from .dispatch import Dispatcher, should_dispatch
from .hub import Hub
from .ledger import Ledger
from .state import StateStore


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or load_config()
    app = FastAPI(title="ridewme-backend")
    app.add_middleware(
        CORSMiddleware, allow_origins=cfg.cors_origins,
        allow_methods=["*"], allow_headers=["*"],
    )
    ledger = Ledger(cfg.database_url)
    state = StateStore(cfg.online_timeout_s)
    hub = Hub()
    dispatcher = Dispatcher()
    app.state.cfg, app.state.ledger, app.state.state = cfg, ledger, state
    app.state.hub, app.state.dispatcher = hub, dispatcher

    # ── REST (fleet app) ──────────────────────────────────────────────
    @app.get("/api/health")
    async def health():
        return {"ok": True, "drivers": len(state.driver_ids()), "subscribers": hub.count}

    @app.get("/api/drivers")
    async def drivers():
        return state.snapshot()

    @app.get("/api/drivers/{driver_id}")
    async def driver(driver_id: str):
        st = state.get(driver_id)
        return st or JSONResponse({"error": "not found"}, status_code=404)

    @app.get("/api/drivers/{driver_id}/events")
    async def driver_events(driver_id: str, limit: int = 100, type: str | None = None):
        return ledger.events_by_driver(driver_id, limit, type)

    @app.get("/api/incidents")
    async def incidents(limit: int = 50):
        return ledger.incidents(limit)

    @app.get("/api/dispatches")
    async def dispatches():
        return dispatcher.dispatched   # audit of confirmed crashes that fired dispatch

    @app.get("/api/drivers/{driver_id}/ledger/verify")
    async def ledger_verify(driver_id: str):
        return ledger.verify_chain(driver_id)

    @app.get("/api/drivers/{driver_id}/ledger")
    async def ledger_rows(driver_id: str, limit: int = 200):
        return ledger.ledger(driver_id, limit)

    # ── WS: daemon -> backend (ingest) ────────────────────────────────
    @app.websocket("/ws/ingest")
    async def ingest(ws: WebSocket):
        if cfg.ingest_token:
            if ws.headers.get("authorization", "") != f"Bearer {cfg.ingest_token}":
                await ws.close(code=4401)
                return
        await ws.accept()
        try:
            while True:
                text = await ws.receive_text()
                try:
                    ev = json.loads(text)
                except ValueError:
                    continue
                ok, err = ledger.append(ev)
                st = state.apply(ev, ok)
                await hub.broadcast({"kind": "state", "driver": state.serialize(st)})
                await hub.broadcast({
                    "kind": "event", "driver_id": ev.get("driver_id"),
                    "verified": ok, "event": ev,
                })
                # The ONLY trigger for emergency dispatch: a verified crash.confirmed (design §8).
                if should_dispatch(ev, ok):
                    record = dispatcher.notify(ev["payload"], ev.get("driver_id"))
                    await hub.broadcast({"kind": "dispatch", "driver_id": ev.get("driver_id"),
                                         "incident": record})
                try:
                    await ws.send_text(json.dumps({
                        "ack": ev.get("seq"), "session_id": ev.get("session_id"),
                        "verified": ok, "error": err,
                    }))
                except Exception:
                    pass
        except WebSocketDisconnect:
            pass

    # ── WS: backend -> fleet app (subscribe) ──────────────────────────
    @app.websocket("/ws/fleet")
    async def fleet(ws: WebSocket):
        await ws.accept()
        await ws.send_text(json.dumps({
            "kind": "snapshot", "drivers": state.snapshot(), "server_ts": round(time.time(), 3),
        }))
        await hub.register(ws)
        try:
            while True:
                await ws.receive_text()  # inbound ignored; keeps the socket + detects close
        except WebSocketDisconnect:
            pass
        finally:
            hub.unregister(ws)

    return app
