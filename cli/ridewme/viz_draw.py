"""Annotate a frame with a face mesh + a level-colored border + HUD.

Used only by the `--viz` debug/demo visualizer. The mesh is a Delaunay
triangulation of the 478 landmark points (computed with OpenCV — no dependency on
MediaPipe's version-specific connection constants), with the eyes + mouth
emphasized in the current drowsiness-level color.
"""

from __future__ import annotations

# BGR colors per drowsiness level
LEVEL_BGR = {
    "awake":  (90, 210, 90),
    "notice": (210, 200, 60),
    "warn":   (0, 180, 255),
    "alarm":  (0, 60, 255),
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

    # Mesh only while capturing the face (calibration); a clean feed after that.
    if m.get("show_mesh", False) and lms and len(lms) >= 468:
        pts = [(int(x), int(y)) for (x, y) in lms]
        _delaunay(cv2, img, pts, (70, 95, 70), w, h)         # dim triangulated mesh
        for i in _EMPHASIS:                                  # emphasize eyes + mouth
            if i < len(pts):
                x, y = pts[i]
                if 0 <= x < w and 0 <= y < h:
                    cv2.circle(img, (x, y), 2, col, -1, cv2.LINE_AA)

    cv2.rectangle(img, (3, 3), (w - 4, h - 4), col, 6)       # level border
    _hud(cv2, img, m, col)
    return img


def _hud(cv2, img, m, col):
    if not m.get("calibrated", True):
        lines = [f"CALIBRATING {int(m.get('calib_progress', 0.0) * 100)}%  ·  look ahead"]
    else:
        s = m.get("signals") or {}
        lines = [
            f"{m.get('level', 'awake').upper()}   score {m.get('score', 0):.0f}",
            f"EAR {s.get('ear', '-')}   PERCLOS {s.get('perclos', '-')}   {m.get('fps', 0):.0f}fps",
        ]
        if m.get("gated"):
            lines.append("PARKED · gated")
    y = 34
    for ln in lines:
        cv2.putText(img, ln, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(img, ln, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, col, 1, cv2.LINE_AA)
        y += 32


def placeholder(text="waiting for camera…"):
    import cv2
    import numpy as np

    img = np.zeros((360, 640, 3), dtype="uint8")
    cv2.putText(img, text, (70, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (130, 130, 130), 2, cv2.LINE_AA)
    return img
