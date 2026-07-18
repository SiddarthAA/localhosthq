"""Fatigue correlation history (design §5) — the crash payload's fatigue_context."""

from ridewme.fatigue import FatigueHistory


def test_empty_context():
    fh = FatigueHistory(window_min=5.0, elevated_score=45.0)
    c = fh.context(now=100.0)
    assert c["was_elevated"] is False and c["recent_max_score"] == 0.0
    assert c["elevated_seconds"] == 0.0


def test_elevated_run_is_measured():
    fh = FatigueHistory(window_min=5.0, elevated_score=45.0)
    t = 0.0
    for _ in range(10):                # 10s calm
        fh.update(t, 10.0); t += 1.0
    for _ in range(40):                # 40s elevated (score 70)
        fh.update(t, 70.0); t += 1.0
    c = fh.context(now=t)
    assert c["was_elevated"] is True
    assert c["recent_max_score"] == 70.0
    assert 35.0 <= c["elevated_seconds"] <= 41.0     # ~40s above threshold


def test_window_drops_old_samples():
    fh = FatigueHistory(window_min=1.0, elevated_score=45.0)   # 60s window
    fh.update(0.0, 90.0)               # old, elevated
    for _ in range(30):
        fh.update(100.0, 5.0)          # far in the future, calm
    c = fh.context(now=100.0)
    assert c["recent_max_score"] == 5.0    # the old elevated sample fell out of the window
    assert c["was_elevated"] is False
