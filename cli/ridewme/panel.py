"""The driver-box panel — the in-cabin view (what the DRIVER sees).

Deliberately plain-language and calm: a quiet status when the driver is fine, a
proportionate escalation as fatigue rises, and a big unmissable "are you OK?"
prompt during a crash-confirmation window. No fleet/ledger/diagnostics — that's
the fleet dashboard's job.

Opt-in via `--panel`; production stays headless. `render(snapshot)` is pure (a
plain dict -> a rich renderable) so it unit-tests without a live terminal.
"""

from __future__ import annotations

# Level -> (driver-facing message, style, glyph)
_LEVEL = {
    "awake":  ("You're alert", "bold green", "✓"),
    "notice": ("Stay sharp", "bold cyan", "•"),
    "warn":   ("Getting drowsy — take a break soon", "bold yellow", "▲"),
    "alarm":  ("WAKE UP  —  PULL OVER", "bold white on red", "⚠"),
}
_WHY = {"perclos": "eyes closing", "blink": "slow blinks",
        "head_nod": "head nodding", "yawn": "yawning"}
_SEV_STYLE = {"minor": "yellow", "moderate": "bright_red", "severe": "bold white on red"}


def _bar(score: float, width: int = 30) -> str:
    filled = int(round(max(0.0, min(100.0, score)) / 100.0 * width))
    return "█" * filled + "░" * (width - filled)


def render(snap: dict):
    """Pure: snapshot dict -> rich renderable for the current driver-box frame."""
    from rich.align import Align
    from rich.console import Group
    from rich.panel import Panel
    from rich.text import Text

    # ── crash takeover: overrides everything ─────────────────────────
    inc = snap.get("incident")
    if inc is not None:
        cd = inc["countdown_s"]
        sev = inc["severity"]
        body = Group(
            Align.center(Text("⚠  IMPACT DETECTED", style="bold white on red")),
            Text(""),
            Align.center(Text(f"{sev.upper()}  ·  {inc['peak_g']}g", style=_SEV_STYLE.get(sev, "red"))),
            Text(""),
            Align.center(Text("Are you OK?", style="bold white")),
            Align.center(Text(f"Calling for help in  {cd:0.0f}s", style="bold yellow")),
            Text(""),
            Align.center(Text("press  [C]  if you're OK        ( [X] simulate )", style="dim white")),
        )
        return Panel(body, title="ridewme · driver box", border_style="red", padding=(1, 2))

    rows = []

    flash = snap.get("flash")
    if flash:
        rows.append(Align.center(Text(f"  {flash['msg']}  ", style=flash["style"])))
        rows.append(Text(""))

    if not snap.get("calibrated"):
        pct = int(snap.get("calib_progress", 0.0) * 100)
        rows += [
            Align.center(Text("⏳  Calibrating…", style="bold cyan")),
            Text(""),
            Align.center(Text("look ahead normally for a few seconds", style="dim")),
            Align.center(Text(f"[{_bar(pct)}] {pct}%", style="cyan")),
        ]
    else:
        gated = snap.get("gated")
        level = snap.get("level", "awake")
        if gated:
            msg, style, glyph = ("Parked — monitoring paused", "dim white", "⏸")
        else:
            msg, style, glyph = _LEVEL.get(level, _LEVEL["awake"])
        score = snap.get("score", 0.0)
        bar_style = {"awake": "green", "notice": "cyan", "warn": "yellow", "alarm": "red"}.get(level, "green")

        rows.append(Align.center(Text(f"{glyph}  {msg}", style=style)))
        rows.append(Text(""))
        rows.append(Align.center(Text(f"[{_bar(score)}]  {score:0.0f}", style=bar_style)))

        why = [_WHY[s] for s in snap.get("fired", []) if s in _WHY]
        if why and not gated and level != "awake":
            rows.append(Text(""))
            rows.append(Align.center(Text("· " + "  ·  ".join(why) + " ·", style="dim yellow")))

    sp = snap.get("speed_mps")
    speed = f"{sp:0.0f} m/s" if isinstance(sp, (int, float)) else "— m/s"
    dot = {"online": "green", "degraded": "yellow", "offline": "red"}.get(snap.get("link"), "green")
    footer = Text.assemble(
        (f"● ", dot), ("recording  ", "dim"),
        (f"{snap.get('driver_id', '?')}  ", "white"),
        (f"{speed}", "dim"),
        ("   [NAIVE]" if snap.get("naive") else "", "bold red"),
    )
    rows += [Text(""), Align.center(footer)]

    from rich.console import Group as _G
    return Panel(_G(*rows), title="ridewme · driver box", border_style=bar_style if snap.get("calibrated") and not snap.get("gated") else "cyan", padding=(1, 2))


class DriverPanel:
    """Live full-screen loop. `snapshot_fn()` returns the current driver state dict."""

    def __init__(self, snapshot_fn):
        self._snap = snapshot_fn

    def run(self, stop_event) -> None:
        try:
            from rich.console import Console
            from rich.live import Live
        except ImportError:
            print("[panel] `rich` not installed — run `uv pip install rich` for --panel. "
                  "Daemon is still running with plain logs.")
            stop_event.wait()
            return

        console = Console()
        if not console.is_terminal:      # piped / not a tty -> no live panel
            print("[panel] no TTY; skipping live panel (daemon running normally).")
            stop_event.wait()
            return

        with Live(render(self._snap()), console=console, screen=True,
                  refresh_per_second=12, transient=True) as live:
            while not stop_event.is_set():
                live.update(render(self._snap()))
                stop_event.wait(0.08)
