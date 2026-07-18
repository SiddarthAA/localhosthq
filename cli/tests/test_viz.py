"""Visualizer render + VizState (the --viz engine X-ray). Needs cv2/numpy;
skips cleanly where they're absent."""

import math

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("cv2")

from ridewme import viz_draw  # noqa: E402
from ridewme.viz_server import VizState  # noqa: E402


def _lms():
    return [(320 + 80 * math.cos(i / 478 * 6.28), 180 + 100 * math.sin(i / 478 * 6.28))
            for i in range(478)]


def test_placeholder():
    assert viz_draw.placeholder().shape == (360, 640, 3)


def test_annotate_full_mesh():
    frame = np.zeros((360, 640, 3), dtype="uint8")
    m = {"level": "warn", "score": 58.0, "calibrated": True, "fps": 15,
         "signals": {"ear": 0.19, "perclos": 0.41}}
    assert viz_draw.annotate(frame, _lms(), m).shape == frame.shape


def test_annotate_no_landmarks_calibrating():
    frame = np.zeros((240, 320, 3), dtype="uint8")
    out = viz_draw.annotate(frame, [], {"level": "awake", "calibrated": False, "calib_progress": 0.5})
    assert out.shape == frame.shape


def test_vizstate_roundtrip():
    vs = VizState()
    vs.update(np.zeros((360, 640, 3), dtype="uint8"), _lms(), {"level": "alarm", "score": 90.0})
    assert len(vs.frame()) > 0                    # real jpeg bytes
    assert vs.metrics()["level"] == "alarm"


def test_vizstate_placeholder_when_no_frame():
    vs = VizState()
    vs.update(None, [], {"level": "awake"})       # synthetic source has no video
    assert len(vs.frame()) > 0                    # falls back to a placeholder jpeg
    assert vs.metrics()["level"] == "awake"
