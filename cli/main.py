"""ridewme edge daemon — entrypoint.

The "driver box": all camera CV, all drowsiness decisions, all crash fusion live
here; it emits signed events only. See CONTRACT.md and ridewme/daemon.py.

    python cli/main.py                 # phone camera + phone sensors (needs sensor-app up)
    python cli/main.py --sim           # fully offline: scripted drowsy + crash scenario
    python cli/main.py --replay clip.mp4
    python cli/main.py --naive         # strawman per-blink detector (demo contrast)
"""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `ridewme` importable

from ridewme.config import load_config  # noqa: E402
from ridewme.daemon import Daemon  # noqa: E402


def _build_sources(cfg, args):
    from ridewme import sources as S

    if args.sim:
        return S.SyntheticFeatureSource(cfg), S.SyntheticSensorSource(cfg, crash_at=args.crash_at)
    if args.replay or cfg.camera_source == "replay":
        cfg.replay_video = args.replay or cfg.replay_video
        return S.ReplayFeatureSource(cfg), S.PhoneSensorSource(cfg)
    return S.PhoneFeatureSource(cfg), S.PhoneSensorSource(cfg)


def _console_listener(daemon) -> None:
    """Demo/console input: 'c'+Enter cancels a pending crash (stands in for the
    physical/voice cancel button); 'x'+Enter simulates an impact (design §10)."""
    if not sys.stdin or not sys.stdin.isatty():
        return
    for line in sys.stdin:
        cmd = line.strip().lower()
        if cmd == "c":
            daemon.cancel_crash()
        elif cmd == "x":
            daemon.simulate_impact()


def main() -> None:
    ap = argparse.ArgumentParser(description="ridewme edge daemon")
    ap.add_argument("--sim", action="store_true", help="run fully offline with scripted inputs")
    ap.add_argument("--replay", metavar="VIDEO", help="use a local video file for frames")
    ap.add_argument("--naive", action="store_true", help="naive per-blink detector (demo)")
    ap.add_argument("--driver-id", help="override DRIVER_ID")
    ap.add_argument("--backend-host", help="override BACKEND_HOST")
    ap.add_argument("--no-audio", action="store_true", help="disable in-cabin audio")
    ap.add_argument("--crash-at", type=float, default=55.0, help="[--sim] crash time in seconds")
    args = ap.parse_args()

    cfg = load_config()
    if args.driver_id:
        cfg.driver_id = args.driver_id
    if args.backend_host:
        cfg.backend_host = args.backend_host
    if args.naive:
        cfg.naive_mode = True
    if args.no_audio:
        cfg.audio_enabled = False

    fsrc, ssrc = _build_sources(cfg, args)
    daemon = Daemon(cfg, fsrc, ssrc)
    threading.Thread(target=_console_listener, args=(daemon,), daemon=True).start()
    daemon.run()


if __name__ == "__main__":
    main()
