"""L5 output — in-cabin audio escalation.

Synthesizes proportionate tones: a soft notice, a two-note chime for warn, and an
urgent repeating alarm that intensifies the longer it's sustained. Non-blocking.
Degrades to a console bell / log line on a headless box or when simpleaudio isn't
available — never crashes the daemon.
"""

from __future__ import annotations

import sys
import time

from .events import ALARM, AWAKE, NOTICE, WARN


class AudioEngine:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._np = None
        self._sa = None
        self._play = None
        self._last_level = AWAKE
        self._last_alarm_t = 0.0
        if enabled:
            try:
                import numpy as np
                import simpleaudio as sa

                self._np, self._sa = np, sa
            except Exception as e:  # pragma: no cover - env-dependent
                print(f"[audio] disabled (no playback backend: {e}); using console bell.")
                self.enabled = False

    def _tone(self, freq: float, ms: float, vol: float):
        np = self._np
        fs = 44100
        n = int(fs * ms / 1000.0)
        t = np.linspace(0.0, ms / 1000.0, n, False)
        # simple attack/decay envelope so it doesn't click
        env = np.minimum(1.0, np.minimum(t * 40.0, (ms / 1000.0 - t) * 40.0))
        wave = np.sin(freq * 2.0 * np.pi * t) * vol * np.clip(env, 0.0, 1.0)
        return (wave * 32767).astype(np.int16), fs

    def _play_buf(self, audio, fs):
        try:
            self._play = self._sa.play_buffer(audio, 1, 2, fs)
        except Exception:
            pass

    def on_escalation(self, level: str, intensity: float) -> None:
        """Call every tick with the *effective* (post-gate) level. Plays on level
        changes and re-fires the alarm periodically, intensifying with `intensity`."""
        now = time.time()
        transition = level != self._last_level
        self._last_level = level

        if not self.enabled:
            if transition and level in (WARN, ALARM):
                sys.stdout.write("\a")  # console bell
                sys.stdout.flush()
            return

        if level == ALARM:
            # repeat every ~1.5s -> 0.7s as intensity climbs; pitch + volume rise too
            period = 1.5 - 0.8 * intensity
            if transition or now - self._last_alarm_t >= period:
                self._last_alarm_t = now
                self._play_buf(*self._tone(660 + 340 * intensity, 260, 0.4 + 0.5 * intensity))
        elif transition and level == WARN:
            a1, fs = self._tone(523, 160, 0.4)
            self._play_buf(a1, fs)
        elif transition and level == NOTICE:
            self._play_buf(*self._tone(440, 120, 0.22))

    def crash_alarm(self, active: bool, intensity: float) -> None:
        """Urgent repeating tone during the crash-confirmation window (design §2, L3).
        An alert driver cancels easily; escalates with `intensity` (time-in-window)."""
        if not active:
            self._last_crash_t = 0.0
            return
        now = time.time()
        if not self.enabled:
            if now - getattr(self, "_last_crash_t", 0.0) >= 1.0:
                self._last_crash_t = now
                sys.stdout.write("\a")
                sys.stdout.flush()
            return
        period = 1.2 - 0.7 * intensity
        if now - getattr(self, "_last_crash_t", 0.0) >= period:
            self._last_crash_t = now
            self._play_buf(*self._tone(880 + 300 * intensity, 220, 0.5 + 0.4 * intensity))

    def stop(self) -> None:
        if self._play is not None:
            try:
                self._play.stop()
            except Exception:
                pass
