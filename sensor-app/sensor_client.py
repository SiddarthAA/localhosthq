#!/usr/bin/env python3
"""OpenCV-compatible client for the sensor-app stream.

Runs on the consumer device (chutney). Pulls the live JPEG video feed from the
shawarma ingest server as an OpenCV frame source, and in parallel subscribes to
the sensor WebSocket so every frame you read carries the most recent sensor
packet.

--- Use it in your own app ------------------------------------------------
    from sensor_client import SensorCam

    cam = SensorCam("shawarma.chipmunk-balance.ts.net")
    while True:
        ok, frame, sensors = cam.read()   # frame: BGR np.ndarray | sensors: dict
        if not ok:
            continue
        # your CV / logic here, e.g.:
        #   gyro = sensors.get("gyro")
        #   gps  = sensors.get("gps")
        #   cv2.imshow("x", frame)
    cam.release()

--- Or pure OpenCV, video only -------------------------------------------
    import cv2
    cap = cv2.VideoCapture("http://shawarma.chipmunk-balance.ts.net:8000/stream/video.mjpeg")
    ok, frame = cap.read()

--- Run the built-in viewer ----------------------------------------------
    python3 sensor_client.py                       # defaults to shawarma
    python3 sensor_client.py --host 100.94.92.13   # or the tailscale IP
"""
import argparse
import json
import threading
import time

import cv2

try:
    import websocket  # pip install websocket-client
except ImportError:
    websocket = None

DEFAULT_HOST = "shawarma.chipmunk-balance.ts.net"
DEFAULT_PORT = 8000


class SensorCam:
    """cv2.VideoCapture-style handle that also carries live sensor data."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, secure: bool = False):
        http = "https" if secure else "http"
        ws = "wss" if secure else "ws"
        self.mjpeg_url = f"{http}://{host}:{port}/stream/video.mjpeg"
        self.sensor_url = f"{ws}://{host}:{port}/ws/stream/sensors"
        self.cap = cv2.VideoCapture(self.mjpeg_url)
        self.sensors: dict = {}
        self._stop = False
        if websocket is not None:
            threading.Thread(target=self._sensor_loop, daemon=True).start()

    def _sensor_loop(self):
        while not self._stop:
            try:
                conn = websocket.create_connection(self.sensor_url, timeout=5)
                while not self._stop:
                    msg = conn.recv()
                    if not msg:
                        break
                    try:
                        self.sensors = json.loads(msg)
                    except ValueError:
                        pass
            except Exception:
                time.sleep(1.0)  # server down or not streaming yet — retry

    def read(self):
        """Return (ok, frame_bgr, sensors_dict). Mirrors cv2.VideoCapture.read()."""
        ok, frame = self.cap.read()
        return ok, frame, dict(self.sensors)

    def isOpened(self) -> bool:
        return self.cap.isOpened()

    def release(self):
        self._stop = True
        self.cap.release()


# --------------------------- built-in viewer ---------------------------
def _f(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def _overlay(frame, s: dict):
    g = s.get("gyro") or {}
    a = s.get("accelG") or {}
    o = s.get("orient") or {}
    gps = s.get("gps") or {}
    lines = [
        f"gyro   a={_f(g.get('alpha'))} b={_f(g.get('beta'))} g={_f(g.get('gamma'))}",
        f"accelG x={_f(a.get('x'))} y={_f(a.get('y'))} z={_f(a.get('z'))}",
        f"compass={_f(o.get('compass'), 0)}",
    ]
    if gps:
        lines.append(f"gps {_f(gps.get('lat'), 5)}, {_f(gps.get('lon'), 5)}")
    y = 24
    for ln in lines:
        cv2.putText(frame, ln, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, ln, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1, cv2.LINE_AA)
        y += 26


def _demo(host, port):
    cam = SensorCam(host, port)
    print(f"video:   {cam.mjpeg_url}")
    print(f"sensors: {cam.sensor_url}")
    if websocket is None:
        print("(install websocket-client to also see sensor data: pip install websocket-client)")
    print("Waiting for the phone to stream… press 'q' in the window to quit.")
    while True:
        ok, frame, sensors = cam.read()
        if not ok or frame is None:
            time.sleep(0.05)
            continue
        _overlay(frame, sensors)
        cv2.imshow("sensor-app · chutney", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="sensor-app OpenCV client")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()
    _demo(args.host, args.port)
