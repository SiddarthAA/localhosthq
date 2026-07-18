"""Annotate a frame with a face mesh + a level-colored border + HUD.

Used only by the `--viz` debug/demo visualizer. The mesh is a Delaunay
triangulation of the 478 landmark points (computed with OpenCV — no dependency on
MediaPipe's version-specific connection constants), with the eyes + mouth
emphasized in the current drowsiness-level color.
"""

from __future__ import annotations

# BGR colors per drowsiness level (aligned to the RidewMe palette: green/cyan/amber/red)
LEVEL_BGR = {
    "awake":  (95, 205, 70),    # success green
    "notice": (238, 211, 34),   # cyan #22d3ee
    "warn":   (35, 166, 245),   # amber
    "alarm":  (68, 68, 239),    # destructive red
}

# landmark indices to emphasize (EAR eye points + mouth)
_EYE_R = [33, 160, 158, 133, 153, 144]
_EYE_L = [362, 385, 387, 263, 373, 380]
_MOUTH = [13, 14, 78, 308, 61, 291, 0, 17]
_EMPHASIS = _EYE_R + _EYE_L + _MOUTH


def _delaunay(cv2, img, pts, color, w, h):
    sub = cv2.Subdiv2D((0, 0, w, h))
    for x, y in pts:
        if 0 <= x < w and 0 <= y < h:
            try:
                sub.insert((float(x), float(y)))
            except cv2.error:
                pass
    for t in sub.getTriangleList():
        a, b, c = (int(t[0]), int(t[1])), (int(t[2]), int(t[3])), (int(t[4]), int(t[5]))
        if all(0 <= x < w and 0 <= y < h for x, y in (a, b, c)):
            cv2.line(img, a, b, color, 1, cv2.LINE_AA)
            cv2.line(img, b, c, color, 1, cv2.LINE_AA)
            cv2.line(img, c, a, color, 1, cv2.LINE_AA)


def annotate(frame, lms, m):
    import cv2

    img = frame.copy()
    h, w = img.shape[:2]
    col = LEVEL_BGR.get(m.get("level", "awake"), LEVEL_BGR["awake"])

    if lms and len(lms) >= 468:
        pts = [(int(x), int(y)) for (x, y) in lms]
        if m.get("show_mesh", False):                        # first ~10s: scan the face (full mesh)
            _delaunay(cv2, img, pts, (70, 95, 70), w, h)
        else:                                                # after: the tracked landmark points
            for x, y in pts:
                if 0 <= x < w and 0 <= y < h:
                    cv2.circle(img, (x, y), 1, (110, 130, 110), -1)
        for i in _EMPHASIS:                                  # eyes + mouth in the level color
            if i < len(pts):
                x, y = pts[i]
                if 0 <= x < w and 0 <= y < h:
                    cv2.circle(img, (x, y), 2, col, -1, cv2.LINE_AA)

    _border(cv2, img, m, col, w, h)
    return img


def _border(cv2, img, m, col, w, h):
    """Level-colored frame; on alarm, a red border that presses inward with intensity."""
    if m.get("level") == "alarm":
        inten = max(0.0, min(1.0, float(m.get("alarm_intensity", 0.0) or 0.0)))
        thick = int(4 + inten * 26)                          # stronger red the longer the eyes stay shut
        off = thick // 2
        cv2.rectangle(img, (off, off), (w - 1 - off, h - 1 - off), (60, 60, 255), thick)
    else:
        cv2.rectangle(img, (2, 2), (w - 3, h - 3), col, 4)


def placeholder(text="waiting for camera…"):
    import cv2
    import numpy as np

    img = np.zeros((360, 640, 3), dtype="uint8")
    cv2.putText(img, text, (70, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (130, 130, 130), 2, cv2.LINE_AA)
    return img
