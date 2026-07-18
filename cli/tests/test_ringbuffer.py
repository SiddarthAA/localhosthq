"""Ring buffer must retain the full window and evict on age (design §3)."""

from ridewme.ringbuffer import Sample, SampleRing


def s(ts, dev=0.0, gyro_mag=0.0, speed=10.0):
    return Sample(ts=ts, accel_g=1.0 + dev, accel_dev_g=dev,
                  gyro=(gyro_mag, 0.0, 0.0), gyro_mag=gyro_mag,
                  speed_mps=speed, gps_available=True)


def test_window_selects_pre_and_post():
    ring = SampleRing(window_s=5.0)
    for i in range(50):
        ring.add(s(ts=i * 0.1))            # 5s at 10 Hz
    win = ring.window(t0=4.0, before=0.5, after=1.0)   # [3.5, 5.0]
    assert win, "window should not be empty"
    assert all(3.5 <= x.ts <= 5.0 for x in win)
    assert min(x.ts for x in win) >= 3.5 and max(x.ts for x in win) <= 5.0


def test_evicts_beyond_window():
    ring = SampleRing(window_s=3.0)
    for i in range(100):
        ring.add(s(ts=i * 0.1))            # newest ts = 9.9
    assert ring.latest().ts == 9.9
    # nothing older than newest-3s should survive
    assert all(x.ts >= 9.9 - 3.0 for x in ring.since(0.0))


def test_since_and_latest():
    ring = SampleRing(window_s=10.0)
    assert ring.latest() is None
    for i in range(20):
        ring.add(s(ts=i * 0.1))
    assert len(ring.since(1.0)) == 10       # ts 1.0..1.9
    assert abs(ring.latest().ts - 1.9) < 1e-6
