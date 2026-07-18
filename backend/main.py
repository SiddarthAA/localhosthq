"""ridewme backend — thin FastAPI relay hub (dumb relay + ledger, no CV, no decisions).

Barebones skeleton: app instance, a /health route, and a placeholder WebSocket stub.
Wiring (event ingest, audit ledger, fleet broadcast) comes later.
"""

from fastapi import FastAPI, WebSocket

app = FastAPI(title="ridewme-backend")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_stub(websocket: WebSocket) -> None:
    # Placeholder stub — accepts then closes. No relay/ledger wiring yet.
    await websocket.accept()
    await websocket.close()
