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


def _wait_for_start(args) -> None:
    """Hold before the ride starts so the operator can set up — start the sensor-app,
    aim the camera, open the dashboard — then press Enter to go. Auto-skips when stdin
    isn't a TTY (scripts / background runs) or when --no-wait is passed."""
    if args.no_wait or not sys.stdin or not sys.stdin.isatty():
        return
    try:
        input(
            "\n  Ready when you are — start the sensor-app, aim the camera, open the dashboard,\n"
            "  then press Enter to begin the ride  (Ctrl-C to abort)… "
        )
    except (EOFError, KeyboardInterrupt):
        print("\n  aborted before start.")
        raise SystemExit(0)
    print("  ▶ ride starting…\n")


def main() -> None:
    # Line-buffer stdout so the [drowsy]/[CRASH] log is never swallowed when the
    # output is a pipe or file (block-buffered by default) and the process is
    # killed — the events still reach the ledger, but the operator's log wouldn't.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="ridewme edge daemon")
    ap.add_argument("--sim", action="store_true", help="run fully offline with scripted inputs")
    ap.add_argument("--replay", metavar="VIDEO", help="use a local video file for frames")
    ap.add_argument("--naive", action="store_true", help="naive per-blink detector (demo)")
    ap.add_argument("--driver-id", help="override DRIVER_ID")
    ap.add_argument("--backend-host", help="override BACKEND_HOST")
    ap.add_argument("--no-audio", action="store_true", help="disable in-cabin audio")
    ap.add_argument("--panel", action="store_true", help="live in-cabin driver panel (needs a TTY)")
    ap.add_argument("--viz", action="store_true", help="serve the engine X-ray visualizer (annotated video + metrics)")
    ap.add_argument("--viz-port", type=int, default=8090, help="visualizer port (default 8090)")
    ap.add_argument("--crash-at", type=float, default=55.0, help="[--sim] crash time in seconds")
    ap.add_argument("--no-wait", action="store_true", help="skip the 'press Enter to start the ride' prompt")
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

    viz_server = None
    if args.viz:
        import socket

        from ridewme.viz_server import VizServer, VizState
        viz = VizState()
        daemon.viz = viz
        viz_server = VizServer(viz, port=args.viz_port)
        viz_server.start()
        print(f"[viz] engine X-ray -> http://{socket.gethostname()}:{args.viz_port}/  (open on the tailnet)")

    _wait_for_start(args)
    threading.Thread(target=_console_listener, args=(daemon,), daemon=True).start()

    if args.panel:
        from ridewme.panel import DriverPanel
        daemon.start()
        try:
            DriverPanel(daemon.panel_snapshot).run(daemon._stop)
        except KeyboardInterrupt:
            pass
        finally:
            daemon.shutdown()
            if viz_server:
                viz_server.stop()
    else:
        try:
            daemon.run()
        finally:
            if viz_server:
                viz_server.stop()


if __name__ == "__main__":
    main()
