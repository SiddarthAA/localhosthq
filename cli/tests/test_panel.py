"""Driver-box panel render (design: what the driver sees). Renders to a recording
console so the visual logic is testable without a live terminal."""

import pytest

pytest.importorskip("rich")
from rich.console import Console  # noqa: E402

from ridewme.panel import render  # noqa: E402

BASE = {
    "driver_id": "driver-1", "session_id": "s-x", "calibrated": True, "calib_progress": 1.0,
    "level": "awake", "score": 5.0, "gated": False, "fired": [], "speed_mps": 12.0,
    "link": "online", "incident": None, "flash": None, "naive": False,
}


def _text(snap):
    c = Console(record=True, force_terminal=True, width=80)
    c.print(render(snap))
    return c.export_text().lower()


def test_alert_is_calm():
    assert "alert" in _text(BASE)


def test_calibrating():
    assert "calibrat" in _text({**BASE, "calibrated": False, "calib_progress": 0.4})


def test_warn_shows_plain_language_why():
    t = _text({**BASE, "level": "warn", "score": 55.0, "fired": ["perclos", "blink"]})
    assert "drowsy" in t
    assert "eyes closing" in t and "slow blinks" in t


def test_alarm_is_loud():
    assert "wake up" in _text({**BASE, "level": "alarm", "score": 85.0})


def test_parked_is_paused():
    assert "parked" in _text({**BASE, "gated": True})


def test_crash_takeover():
    t = _text({**BASE, "incident": {"status": "unconfirmed", "severity": "severe",
                                    "peak_g": 7.5, "countdown_s": 6.0}})
    assert "impact detected" in t
    assert "severe" in t
    assert "help in" in t and "are you ok" in t


def test_resolve_flash():
    t = _text({**BASE, "flash": {"msg": "Cancelled — glad you're OK", "style": "bold green"}})
    assert "cancelled" in t
