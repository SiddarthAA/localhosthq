"""L0 low-light normalization — pure cv2/numpy, so it tests without MediaPipe.
The global brightness check must lift dark frames (bounded), leave bright frames
alone, and never amplify past the gain cap."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("cv2")

from ridewme.perception import normalize_lighting  # noqa: E402


def _luma(frame) -> float:
    import cv2

    return float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()) / 255.0


def test_dark_frame_is_boosted():
    dark = np.full((120, 160, 3), 22, dtype=np.uint8)  # ~0.086 luma
    out, brightness, boosted = normalize_lighting(dark, target=0.42, max_gain=3.0)
    assert boosted is True
    assert brightness < 0.2
    assert _luma(out) > brightness            # shadows lifted


def test_bright_frame_untouched():
    bright = np.full((120, 160, 3), 180, dtype=np.uint8)  # ~0.70
    out, brightness, boosted = normalize_lighting(bright, target=0.42)
    assert boosted is False
    assert brightness > 0.42
    assert out is bright                       # returned as-is, not reprocessed


def test_disabled_never_boosts():
    dark = np.full((120, 160, 3), 22, dtype=np.uint8)
    out, _brightness, boosted = normalize_lighting(dark, enabled=False)
    assert boosted is False
    assert out is dark


def test_gain_is_capped_no_noise_blowup():
    verydark = np.full((120, 160, 3), 4, dtype=np.uint8)  # ~0.016
    out, _brightness, boosted = normalize_lighting(verydark, target=0.42, max_gain=3.0)
    assert boosted is True
    # 3x cap -> ~0.047 mean, nowhere near the 0.42 target (we lift, we don't invent light)
    assert _luma(out) < 0.25
