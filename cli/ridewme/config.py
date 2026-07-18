"""Daemon configuration: operational vars from `.env`, engine tuning as documented
defaults. Network/identity live in `.env` (shared with the backend); the decision
thresholds live here so they're versioned with the code and easy to reason about.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load the repo-root `.env` if python-dotenv is available (optional)."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return
    env = REPO_ROOT / ".env"
    if env.exists():
        load_dotenv(env)


def _b(name: str, default: bool) -> bool:
    v = os.getenv(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Tuning:
    """Engine tuning. Deviation-from-baseline everywhere possible (L2), never raw globals."""

    # L2 — face capture / baseline (first 10s: scan the face, learn this driver's normal)
    calibration_seconds: float = 10.0

    # L1 — signal extraction
    perclos_window_s: float = 60.0
    blink_window_s: float = 30.0
    ear_closed_ratio: float = 0.72            # eyes "closed" when EAR < baseline_open * ratio
    long_blink_ms: float = 400.0
    base_blink_ms: float = 180.0
    headnod_lo_deg: float = 10.0              # pitch drop to start counting (lenient)
    headnod_hi_deg: float = 26.0
    yawn_lo: float = 0.38                     # MAR over baseline (lenient)
    yawn_hi: float = 0.68

    # L3 — drowsiness = a penalty/recovery "debt" (0 = wide awake; climbs with eye closure).
    #   closure = how far EAR fell from open toward shut (0 = open, 1 = fully closed).
    blink_deadzone: float = 0.40              # closure below this = open enough -> NO penalty (normal blinks)
    closure_penalty_per_s: float = 46.0       # penalty rate at full closure; a ~1.5s shut -> alarm
    headnod_penalty_per_s: float = 14.0       # secondary penalties (still tracked)
    yawn_penalty_per_s: float = 11.0
    penalty_activation: float = 0.42          # head-nod / yawn danger above this counts
    recover_per_s: float = 22.0               # eyes open -> recover toward 0 (baseline) each second

    # L5 — escalation on the debt (lenient) + hysteresis (must fall below `down_*` to step down)
    up_notice: float = 14.0
    up_warn: float = 38.0
    up_alarm: float = 62.0
    down_notice: float = 7.0
    down_warn: float = 30.0
    down_alarm: float = 52.0
    alarm_intensify_s: float = 5.0            # seconds of sustained alarm to peak loudness + red border

    # L4 — context gate
    moving_mps: float = 2.0                     # below this GPS speed = "parked", suppress alerts

    # L6 — adaptive duty-cycle
    fps_full: int = 15
    fps_idle: int = 3
    viz_fps: int = 20                           # --viz runs full-rate for a smooth demo feed
    idle_score: float = 8.0                     # below this + no fired signals = candidate for idle
    idle_grace_s: float = 5.0                   # must stay quiet this long before dropping fps

    # ── crash engine (design §11) ────────────────────────────────────
    # Sensor ingest / ring buffer
    sensor_ring_s: float = 5.0                  # rolling buffer length (pre+post window always available)
    accel_baseline_tau_s: float = 3.0           # slow EMA baseline (absorbs gravity + mounting)
    motion_stale_s: float = 3.0                 # motion older than this -> gate assumes moving (fail-safe)
    # Pre-gate
    pregate_min_speed_mps: float = 1.0          # was the vehicle moving before the candidate? (demo: slow-walk ok)
    # Layer 1 — trigger (cheap wake-up, not a decision) — demo-tuned, easy to reach.
    # NB: this is deviation-FROM-BASELINE g (resting ~1g gravity is absorbed), so a
    # ~2g total phone reading = ~1g of spike here.
    accel_spike_g: float = 1.0                  # accel deviation (g) that wakes Layer 2
    # Layer 2 — corroboration over the window — demo-tuned; STILL needs >= 2 of 3 to agree
    crash_l2_window_s: float = 2.0              # score this window around the candidate
    jerk_g_per_s: float = 6.0                   # impact jerk — separates a crash from hard braking
    gyro_axis_dps: float = 60.0                 # per-axis rotation (deg/s); need >= 2 axes (a hand twist hits this)
    gyro_axes_required: int = 2
    speed_drop_mps: float = 4.0                 # sudden GPS speed drop across the window...
    speed_drop_end_mps: float = 4.0             # ...toward (near) zero — impact, not gradual braking
    severity_moderate_g: float = 1.5            # peak-Δg (deviation) severity bands: minor < 1.5 ...
    severity_severe_g: float = 2.5              # ... moderate 1.5–2.5 · severe > 2.5
    # Layer 3 — behavioral confirmation window
    crash_l3_window_s: float = 13.0             # base human window (12–15s)
    crash_l3_window_severe_s: float = 8.0       # severe escalates faster (shorter window)
    deescalate_speed_mps: float = 8.0           # "sustained normal driving" road speed
    deescalate_sustained_s: float = 10.0        # ...held this long -> de-escalate (cancel)
    crash_cooldown_s: float = 5.0               # after a terminal outcome, ignore new candidates

    # correlation (design §5) — crash payload's fatigue_context
    fatigue_window_min: float = 5.0             # look back this far for recent fatigue
    fatigue_elevated_score: float = 45.0        # score >= this (warn) counts as "elevated"

    # emission cadence
    heartbeat_s: float = 5.0
    sample_hz: float = 1.0                       # throttled drowsiness "sample" rate when active

    # uplink resilience — link is "degraded" (catching up) when the durable outbox
    # backlog exceeds this many un-acked events; "online" once drained.
    link_degraded_pending: int = 10


@dataclass
class Config:
    sensor_host: str = "shawarma.chipmunk-balance.ts.net"
    sensor_port: int = 8000
    backend_host: str = "127.0.0.1"
    backend_port: int = 8080
    driver_id: str = "driver-1"
    driver_name: str = "driver-1"                # friendly name for the CLI greeting
    ingest_token: str = ""
    camera_source: str = "phone"                 # phone | replay
    replay_video: str = ""
    audio_enabled: bool = True
    naive_mode: bool = False
    context_gate: bool = False                   # L4 "don't nag a parked driver"; off by default
                                                 # (set CONTEXT_GATE=true for on-road production)
    key_path: str = str(REPO_ROOT / "cli" / "keys" / "driver.key")
    model_path: str = str(REPO_ROOT / "cli" / "models" / "face_landmarker.task")
    outbox_path: str = str(REPO_ROOT / "cli" / "outbox.db")   # durable edge store-and-forward
    tuning: Tuning = field(default_factory=Tuning)

    # ── derived URLs ──────────────────────────────────────────────────
    @property
    def sensor_mjpeg_url(self) -> str:
        return f"http://{self.sensor_host}:{self.sensor_port}/stream/video.mjpeg"

    @property
    def sensor_ws_url(self) -> str:
        return f"ws://{self.sensor_host}:{self.sensor_port}/ws/stream/sensors"

    @property
    def ingest_ws_url(self) -> str:
        return f"ws://{self.backend_host}:{self.backend_port}/ws/ingest"


def load_config() -> Config:
    _load_dotenv()
    driver_id = os.getenv("DRIVER_ID", "driver-1")
    return Config(
        sensor_host=os.getenv("SENSOR_HOST", "shawarma.chipmunk-balance.ts.net"),
        sensor_port=int(os.getenv("SENSOR_PORT", "8000")),
        backend_host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        backend_port=int(os.getenv("BACKEND_PORT", "8080")),
        driver_id=driver_id,
        driver_name=os.getenv("DRIVER_NAME", driver_id),
        ingest_token=os.getenv("INGEST_TOKEN", ""),
        camera_source=os.getenv("CAMERA_SOURCE", "phone").strip().lower(),
        replay_video=os.getenv("REPLAY_VIDEO", ""),
        audio_enabled=_b("AUDIO_ENABLED", True),
        naive_mode=_b("NAIVE_MODE", False),
        context_gate=_b("CONTEXT_GATE", False),
        outbox_path=os.getenv("OUTBOX_PATH", str(REPO_ROOT / "cli" / "outbox.db")),
    )
