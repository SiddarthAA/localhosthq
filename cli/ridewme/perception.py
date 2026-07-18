"""L0 — Perception. MediaPipe FaceLandmarker -> per-frame face geometry.

The cheapest, least-differentiated layer: commodity landmarks. We turn them into
`RawFeatures` (EAR, MAR, head pitch, blendshape corroboration). MediaPipe/OpenCV
are imported lazily so the decision core and its tests never need them.
"""

from __future__ import annotations

import contextlib
import os
import urllib.request
from pathlib import Path

from .signals import RawFeatures

# Quiet MediaPipe / TF-Lite / glog before they load (must be set pre-import).
os.environ.setdefault("GLOG_minloglevel", "3")
os.environ.setdefault("GLOG_logtostderr", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


@contextlib.contextmanager
def _quiet_native_stderr():
    """Silence C++ (glog/absl/TF-Lite) chatter written straight to fd 2 during init."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        saved = os.dup(2)
        os.dup2(devnull, 2)
    except OSError:
        yield
        return
    try:
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

# MediaPipe 478-landmark indices.
_RIGHT_EYE = [33, 160, 158, 133, 153, 144]   # p1(outer) p2 p3 p4(inner) p5 p6
_LEFT_EYE = [362, 385, 387, 263, 373, 380]
_MOUTH = dict(upper=13, lower=14, left=78, right=308)


def ensure_model(path: str | Path) -> Path:
    """Download the FaceLandmarker task model to `path` if it isn't there yet."""
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    print(f"[perception] downloading face landmarker model -> {p} ...")
    urllib.request.urlretrieve(MODEL_URL, p)
    if not p.exists() or p.stat().st_size == 0:
        raise RuntimeError(f"model download failed: {p}")
    print("[perception] model ready.")
    return p


def _ear(pts, idx) -> float:
    import numpy as np

    p = [np.array(pts[i], dtype=float) for i in idx]
    vert = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    horiz = 2.0 * np.linalg.norm(p[0] - p[3])
    return float(vert / horiz) if horiz > 1e-6 else 0.0


def _mar(pts) -> float:
    import numpy as np

    up = np.array(pts[_MOUTH["upper"]], dtype=float)
    lo = np.array(pts[_MOUTH["lower"]], dtype=float)
    le = np.array(pts[_MOUTH["left"]], dtype=float)
    ri = np.array(pts[_MOUTH["right"]], dtype=float)
    horiz = np.linalg.norm(le - ri)
    return float(np.linalg.norm(up - lo) / horiz) if horiz > 1e-6 else 0.0


def _pitch_deg(matrix) -> float:
    """Head pitch (degrees) from the 4x4 facial transformation matrix. Sign
    convention is absorbed by L2 baseline; nod is measured as drop from neutral."""
    import math

    import numpy as np

    m = np.array(matrix, dtype=float).reshape(4, 4)
    r = m[:3, :3]
    sy = math.sqrt(r[0, 0] ** 2 + r[1, 0] ** 2)
    return math.degrees(math.atan2(-r[2, 0], sy))


class FaceMeshDetector:
    """Wraps MediaPipe FaceLandmarker in VIDEO mode; returns RawFeatures per frame."""

    def __init__(self, model_path: str | Path):
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
        except ImportError as e:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "mediapipe is required for the phone/replay camera path "
                "(`uv pip install -r cli/requirements.txt`)."
            ) from e
        self._mp = mp
        ensure_model(model_path)
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        with _quiet_native_stderr():   # hide glog/absl/XNNPACK init spam
            self._detector = vision.FaceLandmarker.create_from_options(opts)
        self.landmarks_px: list = []   # last frame's 478 landmark pixel points (for --viz overlay)

    def detect(self, frame_bgr, ts_ms: int) -> RawFeatures:
        import cv2

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_bgr.shape[:2]
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        res = self._detector.detect_for_video(mp_image, int(ts_ms))
        if not res.face_landmarks:
            self.landmarks_px = []
            return RawFeatures(face_present=False, ear=0.0, mar=0.0, pitch_deg=0.0)

        lm = res.face_landmarks[0]
        pts = [(p.x * w, p.y * h) for p in lm]
        self.landmarks_px = pts
        ear = 0.5 * (_ear(pts, _RIGHT_EYE) + _ear(pts, _LEFT_EYE))
        mar = _mar(pts)
        pitch = (
            _pitch_deg(res.facial_transformation_matrixes[0])
            if res.facial_transformation_matrixes else 0.0
        )

        blinks = {}
        if res.face_blendshapes:
            blinks = {c.category_name: c.score for c in res.face_blendshapes[0]}
        eyeblink = 0.5 * (blinks.get("eyeBlinkLeft", 0.0) + blinks.get("eyeBlinkRight", 0.0))
        jawopen = blinks.get("jawOpen", 0.0)

        return RawFeatures(
            face_present=True, ear=ear, mar=mar, pitch_deg=pitch,
            eyeblink=eyeblink, jawopen=jawopen,
        )

    def close(self) -> None:
        try:
            self._detector.close()
        except Exception:
            pass
