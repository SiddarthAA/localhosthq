"""The `--viz` debug/demo visualizer server (edge-local, opt-in).

A tiny stdlib HTTP server the daemon runs alongside the engines. Serves:
  GET /               -> the self-contained visualizer page (viz.html)
  GET /stream.mjpeg   -> annotated live video (MJPEG)
  GET /events         -> live metrics (Server-Sent Events, ~10 Hz)

This streams *annotated* video out of the edge — a developer X-ray for demos, NOT
the product data path. The fleet backend/dashboard still receive signed events
only. Bind is edge-local; reach it over the tailnet at http://<host>:8090/.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_HTML = (Path(__file__).parent / "viz.html").read_bytes()


class VizState:
    """Shared latest annotated JPEG + metrics. `update()` runs in the camera thread
    (annotate + encode once per frame); the server threads just relay bytes."""

    def __init__(self):
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._metrics: dict = {}
        self._placeholder: bytes | None = None

    def update(self, frame, lms, metrics: dict) -> None:
        if frame is not None:
            try:
                import cv2

                from . import viz_draw
                ann = viz_draw.annotate(frame, lms, metrics)
                ok, buf = cv2.imencode(".jpg", ann, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    with self._lock:
                        self._jpeg = buf.tobytes()
            except Exception:
                pass
        with self._lock:
            self._metrics = metrics

    def frame(self) -> bytes:
        with self._lock:
            if self._jpeg is not None:
                return self._jpeg
        return self._placeholder_jpeg()

    def metrics(self) -> dict:
        with self._lock:
            return dict(self._metrics)

    def _placeholder_jpeg(self) -> bytes:
        if self._placeholder is None:
            try:
                import cv2

                from . import viz_draw
                ok, buf = cv2.imencode(".jpg", viz_draw.placeholder())
                self._placeholder = buf.tobytes() if ok else b""
            except Exception:
                self._placeholder = b""
        return self._placeholder


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silence per-request logging

    def do_GET(self):
        viz: VizState = self.server.viz  # type: ignore[attr-defined]
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_bytes(_HTML, "text/html; charset=utf-8")
        elif path == "/stream.mjpeg":
            self._mjpeg(viz)
        elif path == "/events":
            self._sse(viz)
        else:
            self.send_error(404)

    def _send_bytes(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _mjpeg(self, viz: VizState):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                jpeg = viz.frame()
                if jpeg:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                time.sleep(1 / 25)
        except (BrokenPipeError, ConnectionResetError, ValueError):
            pass

    def _sse(self, viz: VizState):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                payload = json.dumps(viz.metrics(), separators=(",", ":"))
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError, ValueError):
            pass


class VizServer:
    def __init__(self, viz: VizState, port: int = 8090, host: str = "0.0.0.0"):
        self._httpd = ThreadingHTTPServer((host, port), _Handler)
        self._httpd.viz = viz  # type: ignore[attr-defined]
        self.port = port

    def start(self) -> None:
        threading.Thread(target=self._httpd.serve_forever, name="viz", daemon=True).start()

    def stop(self) -> None:
        try:
            self._httpd.shutdown()
        except Exception:
            pass
