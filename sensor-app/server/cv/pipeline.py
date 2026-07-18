"""Background CV worker (runs on shawarma).

Decodes each incoming frame, computes lightweight metrics (brightness, motion),
and re-emits the frame as the processed feed. By default it emits the frame
UNCHANGED -- a clean video passthrough, no overlays.

To add real CV later: in `process()`, draw on a copy of `frame` and return it as
`annotated` (instead of None). Only then is the frame re-encoded and the drawing
shows up on /stream/cv.mjpeg. Metrics you add to the dict appear on
/latest/cv and /ws/stream/cv.
"""
import asyncio
import time

import cv2
import numpy as np

from ..hub import hub


async def cv_worker() -> None:
    prev_gray = None
    async with hub.sub_frames() as q:
        while True:
            jpeg = await q.get()
            metrics, cv_jpeg, prev_gray = await asyncio.to_thread(_run, jpeg, prev_gray)
            if cv_jpeg is not None:
                hub.publish_cv_frame(cv_jpeg)
            if metrics is not None:
                hub.publish_cv(metrics)


def _run(jpeg: bytes, prev_gray):
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None, None, prev_gray
    metrics, annotated, gray = process(frame, prev_gray)
    cv_jpeg = jpeg  # clean passthrough: re-emit original bytes, no re-encode
    if annotated is not None:
        ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            cv_jpeg = buf.tobytes()
    return metrics, cv_jpeg, gray


def process(frame, prev_gray):
    """Hook your CV here. `frame` is a BGR numpy array (H, W, 3).

    Return (metrics_dict, annotated_frame_or_None, gray_for_next_call).
    Return annotated=None (default) to emit the clean original frame.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    motion = 0.0
    if prev_gray is not None and prev_gray.shape == gray.shape:
        motion = float(cv2.absdiff(prev_gray, gray).mean())
    metrics = {
        "t": time.time(),
        "width": w,
        "height": h,
        "brightness": round(float(gray.mean()), 2),
        "motion": round(motion, 3),
    }
    return metrics, None, gray
