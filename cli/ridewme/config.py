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

    # L2 — calibration
    calibration_seconds: float = 12.0

    # L1 — signal windows
    perclos_window_s: float = 60.0            # clinical PERCLOS window
    blink_window_s: float = 30.0              # window for blink-rate
    ear_closed_ratio: float = 0.72            # eye "closed" if EAR < baseline_open * ratio
    long_blink_ms: float = 400.0              # a slow/long blink — the real drowsiness tell
    base_blink_ms: float = 180.0              # a normal alert blink

    # L1 — thresholds for the corroboration danger channels (deviation from baseline)
    perclos_lo: float = 0.08                  # PERCLOS at/below this = alert
    perclos_hi: float = 0.40                  # PERCLOS at/above this = severe
    headnod_lo_deg: float = 8.0               # pitch drop from neutral to start counting
    headnod_hi_deg: float = 25.0              # pitch drop = full nod
    yawn_lo: float = 0.35                     # MAR (mouth-aspect) over baseline
    yawn_hi: float = 0.65

    # L3 — trust engine (leaky integrator + corroboration)
    activation: float = 0.40                  # a channel "fires" above this danger
    single_cap_other: float = 0.25            # lone non-PERCLOS signal -> whisper (notice ceiling)
    single_cap_perclos: float = 0.60          # lone PERCLOS can reach warn, never alarm
    pair_cap: float = 0.72                     # two agreeing -> up to warn/low-alarm
    perclos_override: float = 0.82            # sustained eye-closure is itself dangerous
    perclos_override_target: float = 0.70
    weights: dict = field(default_factory=lambda: {
        "perclos": 0.50, "blink": 0.20, "head_nod": 0.15, "yawn": 0.15,
    })
    rise_tau_s: float = 3.0                    # score climbs over seconds (persistence)
    fall_tau_s: float = 6.0                    # backs off slower (no flapping), still recovers

    # L5 — escalation thresholds (up) and hysteresis (down must fall below these)
    up_notice: float = 20.0
    up_warn: float = 45.0
    up_alarm: float = 72.0
    down_notice: float = 12.0                  # alarm/warn -> below this to leave notice
    down_warn: float = 38.0
    down_alarm: float = 62.0
    alarm_intensify_s: float = 8.0             # seconds in alarm to reach peak intensity

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
    pregate_min_speed_mps: float = 2.0          # was the vehicle moving before the candidate?
    # Layer 1 — trigger (cheap wake-up, not a decision)
    accel_spike_g: float = 2.5                  # accel deviation (g) that wakes Layer 2
    # Layer 2 — corroboration over the window
    crash_l2_window_s: float = 2.0              # score this window around the candidate
    jerk_g_per_s: float = 20.0                  # impact jerk — separates a crash from hard braking
    gyro_axis_dps: float = 150.0                # per-axis rotation (deg/s); need >= 2 axes
    gyro_axes_required: int = 2
    speed_drop_mps: float = 6.0                 # sudden GPS speed drop across the window...
    speed_drop_end_mps: float = 3.0             # ...toward (near) zero — impact, not gradual braking
    severity_moderate_g: float = 3.5            # peak-Δg severity bands: minor < 3.5 ...
    severity_severe_g: float = 6.0              # ... moderate 3.5–6 · severe > 6
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
    )
