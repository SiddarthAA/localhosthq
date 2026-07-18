"""Ingest side: WebSocket endpoints the phone (iphone-xr) pushes into.

Prints a green "phone connected" / red "phone disconnected" line to the CLI.
The phone opens two sockets (sensors + video); they're counted so one phone
logs a single connect (first socket up) and a single disconnect (last down).
"""
import json
import sys
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .hub import hub

router = APIRouter()

_TTY = sys.stdout.isatty()
_active_phones = 0


def _color(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def _phone_event(connected: bool, client: str) -> None:
    global _active_phones
    if connected:
        _active_phones += 1
        if _active_phones == 1:
            print(_color("1;32", "● phone connected") + "   " + _color("2", client), flush=True)
    else:
        _active_phones = max(0, _active_phones - 1)
        if _active_phones == 0:
            print(_color("1;31", "○ phone disconnected") + "   " + _color("2", client), flush=True)


@router.websocket("/ws/sensors")
async def ws_sensors(ws: WebSocket) -> None:
    """Phone -> server. Text frames, one JSON sensor packet each (~60 Hz)."""
    await ws.accept()
    client = ws.client.host if ws.client else "?"
    _phone_event(True, client)
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
    finally:
        _phone_event(False, client)


@router.websocket("/ws/video")
async def ws_video(ws: WebSocket) -> None:
    """Phone -> server. Binary frames, one JPEG image each."""
    await ws.accept()
    client = ws.client.host if ws.client else "?"
    _phone_event(True, client)
    try:
        while True:
            jpeg = await ws.receive_bytes()
            hub.publish_frame(jpeg)
    except WebSocketDisconnect:
        pass
    finally:
        _phone_event(False, client)
