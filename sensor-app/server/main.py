"""sensor-app ingest + processing server (runs on shawarma).

    uvicorn server.main:app --host 0.0.0.0 --port 8000

Phone client:  /            Dashboard:  /dashboard
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
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


@app.get("/emit")
@app.get("/phone")
async def emit():
    return FileResponse(WEB_DIR / "emit.html")


@app.get("/dashboard")
async def dashboard():
    return FileResponse(WEB_DIR / "dashboard.html")


# Static files (landing page at /, plus /app.js, /dashboard.js) served last so
# the explicit routes above win.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
