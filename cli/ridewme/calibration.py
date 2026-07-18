"""L2 — Personal baseline calibration.

The first ~12s learn *this* driver's normal: open-eye EAR, neutral head pitch,
neutral mouth-aspect. Everything downstream is measured as deviation from this
baseline, not a global constant — which is why the engine doesn't false-fire
across different faces the way generic threshold systems do.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .signals import RawFeatures


@dataclass
class Baseline:
    ready: bool
    ear_open: float
    closed_ear_threshold: float
    pitch_neutral: float
    mar_neutral: float
    samples: int = 0

    @classmethod
    def pending(cls) -> "Baseline":
        # Conservative placeholders used before calibration completes.
        return cls(
            ready=False, ear_open=0.30, closed_ear_threshold=0.18,
            pitch_neutral=0.0, mar_neutral=0.0, samples=0,
        )


class BaselineCalibrator:
    _MIN_SAMPLES = 10

    def __init__(self, tuning):
        self.t = tuning
        self._start: float | None = None
        self._ear: list[float] = []
        self._pitch: list[float] = []
        self._mar: list[float] = []
        self._baseline = Baseline.pending()

    @property
    def baseline(self) -> Baseline:
        return self._baseline

    @property
    def ready(self) -> bool:
        return self._baseline.ready

    def progress(self, now: float) -> float:
        """0..1 fraction of the calibration window elapsed."""
        if self._start is None:
            return 0.0
        return min(1.0, (now - self._start) / self.t.calibration_seconds)

    def update(self, raw: RawFeatures, ts: float) -> Baseline:
        if self._baseline.ready:
            return self._baseline
        if self._start is None:
            self._start = ts
        if raw.face_present and raw.ear is not None:
            self._ear.append(raw.ear)
            self._pitch.append(raw.pitch_deg)
            self._mar.append(raw.mar)
        if ts - self._start >= self.t.calibration_seconds and len(self._ear) >= self._MIN_SAMPLES:
            self._finalize()
        return self._baseline

    def _finalize(self) -> None:
        # During calibration the driver is asked to look ahead normally, so the
        # bulk of EAR samples are open-eye. Use the median as the open reference.
        ear_open = statistics.median(self._ear)
        self._baseline = Baseline(
            ready=True,
            ear_open=ear_open,
            closed_ear_threshold=ear_open * self.t.ear_closed_ratio,
            pitch_neutral=statistics.median(self._pitch),
            mar_neutral=statistics.median(self._mar),
            samples=len(self._ear),
        )
