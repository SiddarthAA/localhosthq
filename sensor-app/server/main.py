"""sensor-app ingest + processing server (runs on shawarma).

    uvicorn server.main:app --host 0.0.0.0 --port 8000

The only UI page is /emit (root / redirects to it). Everything else is data:
ingest sockets (/ws/sensors, /ws/video) and consumer endpoints (/stream/*, /latest/*, /ws/stream/*).
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .consumers import router as consumers_router
from .cv.pipeline import cv_worker
from .ingest import router as ingest_router

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cv_worker())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="sensor-app (shawarma)", lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(consumers_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/emit")


@app.get("/emit")
async def emit():
    return FileResponse(WEB_DIR / "emit.html")


# Static assets (/app.js, /ui.css) served last so the routes above win.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
