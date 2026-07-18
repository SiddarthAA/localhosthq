"""Input sources for the daemon's two parallel readers.

Two abstractions, each with a freshest-sample buffer so nothing blocks:
  * FeatureSource  -> per-frame `RawFeatures` for the camera/decision loop (L0-L5).
  * SensorSource   -> latest phone sensor packet for the crash-fusion loop.

Production frames come only from the phone (sensor-app MJPEG), per the design.
`Replay*` (a local video file) and `Synthetic*` (scripted, no camera/sensors) let
the full engine run and be demoed while the sensor server is down.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from typing import Protocol

from .signals import RawFeatures


class FeatureSource(Protocol):
    def read(self) -> tuple[bool, RawFeatures | None, float]: ...
    def close(self) -> None: ...


class SensorSource(Protocol):
    def drain(self) -> list[dict]: ...       # ALL samples since last call (crash engine — no loss)
    def latest(self) -> dict: ...            # freshest only (convenience)
    @property
    def connected(self) -> bool: ...
    def close(self) -> None: ...


# ── phone video (production frame path) ───────────────────────────────
class _FreshestFrame:
    """Background thread that keeps only the newest frame from a cv2 source."""

    def __init__(self, url: str):
        import cv2

        self._cv2 = cv2
        self._url = url
        self._cap = cv2.VideoCapture(url)
        self._frame = None
        self._lock = threading.Lock()
        self._stop = False
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._stop:
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.2)
                # reconnect on drop
                self._cap.release()
                self._cap = self._cv2.VideoCapture(self._url)
                continue
            with self._lock:
                self._frame = frame

    def latest(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def close(self):
        self._stop = True
        self._cap.release()


class PhoneFeatureSource:
    def __init__(self, cfg):
        from .perception import FaceMeshDetector

        self._reader = _FreshestFrame(cfg.sensor_mjpeg_url)
        self._det = FaceMeshDetector(cfg.model_path)
        self._t0 = time.time()

    def read(self):
        frame = self._reader.latest()
        now = time.time()
        if frame is None:
            return (False, None, now)
        raw = self._det.detect(frame, int((now - self._t0) * 1000))
        return (True, raw, now)

    def close(self):
        self._reader.close()
        self._det.close()


class ReplayFeatureSource:
    """Sequential local-video source for offline dev/demo (loops the file)."""

    def __init__(self, cfg):
        import cv2

        from .perception import FaceMeshDetector

        self._cv2 = cv2
        self._cap = cv2.VideoCapture(cfg.replay_video)
        self._det = FaceMeshDetector(cfg.model_path)
        self._n = 0
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 15.0

    def read(self):
        ok, frame = self._cap.read()
        if not ok:
            self._cap.set(self._cv2.CAP_PROP_POS_FRAMES, 0)  # loop
            ok, frame = self._cap.read()
            if not ok:
                return (False, None, time.time())
        self._n += 1
        raw = self._det.detect(frame, int(self._n / self._fps * 1000))
        return (True, raw, time.time())

    def close(self):
        self._cap.release()
        self._det.close()


# ── synthetic (no camera, no sensor server) ───────────────────────────
class SyntheticFeatureSource:
    """A scripted driver: calibrate -> alert -> drowsy (long blinks + nods +
    yawns, drives the engine to alarm) -> recover. No MediaPipe needed."""

    def __init__(self, _cfg=None):
        self._t0 = time.monotonic()

    def read(self):
        e = time.monotonic() - self._t0
        open_ear, closed_ear = 0.30, 0.09
        pitch, mar = 0.0, 0.0
        if e < 12:                       # L2 calibration window: alert, short blinks
            ear = closed_ear if (e % 3.0) < 0.15 else open_ear
        elif e < 18:                     # alert driving
            ear = closed_ear if (e % 3.5) < 0.15 else open_ear
        elif e < 30:                     # EARLY drowsy: long blinks, occasional nod/yawn
            ear = closed_ear if (e % 2.2) < 0.7 else (open_ear - 0.05)
            pitch = -16.0 if (e % 5.0) < 2.5 else -3.0
            mar = 0.50 if (e % 8.0) < 1.2 else 0.0
        elif e < 55:                     # DEEP drowsy (worsening): sustained droop + frequent
            ear = closed_ear if (e % 1.6) < 0.9 else (open_ear - 0.10)   # ~56% closed
            pitch = -20.0                                                # head drooping, sustained
            mar = 0.55 if (e % 4.0) < 1.6 else 0.15
        else:                            # recovery
            ear = closed_ear if (e % 3.0) < 0.15 else open_ear
        return (True, RawFeatures(face_present=True, ear=ear, mar=mar, pitch_deg=pitch), time.time())

    def close(self):
        pass


# ── phone sensors (production) ────────────────────────────────────────
class PhoneSensorSource:
    def __init__(self, cfg):
        self._url = cfg.sensor_ws_url
        self._latest: dict = {}
        self._buf: deque = deque(maxlen=2000)   # capture EVERY packet (crashes peak <100 ms)
        self._lock = threading.Lock()
        self._connected = False
        self._stop = False
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            import websocket  # websocket-client
        except ImportError:
            return
        while not self._stop:
            try:
                conn = websocket.create_connection(self._url, timeout=5)
                self._connected = True
                while not self._stop:
                    msg = conn.recv()
                    if not msg:
                        break
                    try:
                        pkt = json.loads(msg)
                    except ValueError:
                        continue
                    self._latest = pkt
                    with self._lock:
                        self._buf.append(pkt)
            except Exception:
                self._connected = False
                time.sleep(1.0)

    def drain(self) -> list[dict]:
        with self._lock:
            out = list(self._buf)
            self._buf.clear()
        return out

    def latest(self) -> dict:
        return dict(self._latest)

    @property
    def connected(self) -> bool:
        return self._connected

    def close(self):
        self._stop = True


class SyntheticSensorSource:
    """Scripted sensor stream. Normal driving, then an optional **severe crash** at
    `crash_at`: a ~0.4s impact (huge accel + jerk + rotation on 2 axes + speed→0)
    followed by the vehicle stopped-and-staying-stopped, so Layer 2 corroborates
    and Layer 3 confirms. `drain()` returns one freshly-synthesized sample per call."""

    def __init__(self, _cfg=None, crash_at: float | None = 55.0):
        self._t0 = time.monotonic()
        self.crash_at = crash_at

    def _sample(self, e: float) -> dict:
        speed = min(12.0, e * 2.0)
        accelG = {"x": 0.0, "y": 0.0, "z": 9.8}
        gyro = {"alpha": 1.0, "beta": 1.0, "gamma": 1.0}
        if self.crash_at is not None and e >= self.crash_at:
            speed = 0.0                                   # crashed -> stopped, stays stopped
            if e - self.crash_at < 0.4:                   # the impact itself
                accelG = {"x": 70.0, "y": 20.0, "z": 9.8}  # ~7.4g peak -> severe
                gyro = {"alpha": 260.0, "beta": 210.0, "gamma": 30.0}  # 2 axes hot
        return {
            "device": "sim", "t": time.time() * 1000.0, "mono": e * 1000.0, "interval": 0.02,
            "accel": {"x": accelG["x"], "y": accelG["y"], "z": accelG["z"] - 9.8},
            "accelG": accelG, "gyro": gyro,
            "orient": {"alpha": 0.0, "beta": 0.0, "gamma": 0.0, "compass": 90.0},
            "gps": {"lat": 12.97, "lon": 77.59, "alt": 900.0, "acc": 5.0,
                    "speed": speed, "heading": 90.0},
        }

    def drain(self) -> list[dict]:
        return [self._sample(time.monotonic() - self._t0)]

    def latest(self) -> dict:
        return self._sample(time.monotonic() - self._t0)

    @property
    def connected(self) -> bool:
        return True

    def close(self):
        pass
