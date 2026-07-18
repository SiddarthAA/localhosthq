"""Ingest side: WebSocket endpoints the phone (iphone-xr) pushes into."""
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .hub import hub

router = APIRouter()


@router.websocket("/ws/sensors")
async def ws_sensors(ws: WebSocket) -> None:
    """Phone -> server. Text frames, one JSON sensor packet each (~60 Hz)."""
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            try:
                data = json.loads(msg)
            except (ValueError, TypeError):
                continue
            data["recv_t"] = time.time()  # server receive time (wall clock)
            hub.publish_sensors(data)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/video")
async def ws_video(ws: WebSocket) -> None:
    """Phone -> server. Binary frames, one JPEG image each."""
    await ws.accept()
    try:
        while True:
            jpeg = await ws.receive_bytes()
            hub.publish_frame(jpeg)
    except WebSocketDisconnect:
        pass
