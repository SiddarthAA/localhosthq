"""Consumer side: what dashboards / your apps read from shawarma.

  GET  /latest/sensors        newest sensor packet (JSON)
  GET  /latest/cv             newest CV metrics (JSON)
  GET  /latest/frame.jpg      newest raw frame (JPEG)
  GET  /latest/cv_frame.jpg   newest CV-annotated frame (JPEG)
  GET  /stream/video.mjpeg    live raw video, OpenCV-friendly
  GET  /stream/cv.mjpeg       live server-processed video
  WS   /ws/stream/sensors     live sensor push (JSON text)
  WS   /ws/stream/frames      live raw video push (binary JPEG)
  WS   /ws/stream/cv          live CV-metrics push (JSON text)
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .hub import hub

router = APIRouter()

_BOUNDARY = b"frame"


def _mjpeg_part(jpeg: bytes) -> bytes:
    return (
        b"--" + _BOUNDARY + b"\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
    )


def _mjpeg_stream(sub_factory, latest_getter):
    async def gen():
        async with sub_factory() as q:
            first = latest_getter()
            if first is not None:
                yield _mjpeg_part(first)
            while True:
                yield _mjpeg_part(await q.get())

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/latest/sensors")
async def latest_sensors():
    return JSONResponse(hub.latest_sensors)


@router.get("/latest/cv")
async def latest_cv():
    return JSONResponse(hub.latest_cv)


@router.get("/latest/frame.jpg")
async def latest_frame():
    if hub.latest_frame is None:
        return Response(status_code=503)
    return Response(content=hub.latest_frame, media_type="image/jpeg")


@router.get("/latest/cv_frame.jpg")
async def latest_cv_frame():
    if hub.latest_cv_frame is None:
        return Response(status_code=503)
    return Response(content=hub.latest_cv_frame, media_type="image/jpeg")


@router.get("/stream/video.mjpeg")
async def stream_mjpeg():
    """Raw camera feed. OpenCV drop-in:

        cap = cv2.VideoCapture("http://shawarma.chipmunk-balance.ts.net:8000/stream/video.mjpeg")
    """
    return _mjpeg_stream(hub.sub_frames, lambda: hub.latest_frame)


@router.get("/stream/cv.mjpeg")
async def stream_cv_mjpeg():
    """Server-processed feed: frames annotated by the CV worker on shawarma."""
    return _mjpeg_stream(hub.sub_cv_frames, lambda: hub.latest_cv_frame)


@router.websocket("/ws/stream/sensors")
async def stream_sensors(ws: WebSocket):
    await ws.accept()
    async with hub.sub_sensors() as q:
        try:
            while True:
                await ws.send_text(json.dumps(await q.get()))
        except WebSocketDisconnect:
            pass


@router.websocket("/ws/stream/frames")
async def stream_frames(ws: WebSocket):
    await ws.accept()
    async with hub.sub_frames() as q:
        try:
            while True:
                await ws.send_bytes(await q.get())
        except WebSocketDisconnect:
            pass


@router.websocket("/ws/stream/cv")
async def stream_cv(ws: WebSocket):
    await ws.accept()
    async with hub.sub_cv() as q:
        try:
            while True:
                await ws.send_text(json.dumps(await q.get()))
        except WebSocketDisconnect:
            pass
