import { useEffect, useState } from 'react'
import { AlertOctagon, Ambulance, MapPin, ShieldCheck, X } from 'lucide-react'
import { useLive } from '@/lib/useLive'
import { liveSource } from '@/lib/fleet'
import { useMode } from '@/lib/hooks'
import { Button } from '@/components/ui/button'

export default function CrashPanel() {
  const d = useLive()
  const [mode] = useMode()
  const inc = d.active_incident
  const [, force] = useState(0)

  useEffect(() => {
    if (inc?.status !== 'unconfirmed') return
    const t = setInterval(() => force((n) => n + 1), 100)
    return () => clearInterval(t)
  }, [inc?.status, inc?.incident_id])

  if (!inc) {
    return (
      <section className="flex h-full flex-col border border-border bg-card">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <ShieldCheck className="size-4 text-primary" />
          <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">Crash detection</h2>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
          <div className="flex size-12 items-center justify-center border border-primary/30 bg-primary/5">
            <ShieldCheck className="size-6 text-primary" />
          </div>
          <p className="text-sm font-semibold">No active incident</p>
          <p className="max-w-[26ch] text-xs text-muted-foreground">
            Fusing accelerometer, gyroscope &amp; GPS. A crash is called only when ≥2 of 3 agree.
          </p>
          <div className="mt-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span className="size-1.5 rounded-full bg-primary" />
            link {d.link} · {d.pending} buffered
          </div>
        </div>
      </section>
    )
  }

  const remaining =
    inc.status === 'unconfirmed'
      ? Math.max(0, inc.cancel_window_s - (Date.now() - inc.ts_detected) / 1000)
      : 0
  const pct = inc.status === 'unconfirmed' ? (remaining / inc.cancel_window_s) * 100 : 0

  const tone =
    inc.status === 'confirmed'
      ? { c: '#ff5148', label: 'Crash confirmed · dispatched' }
      : inc.status === 'cancelled'
        ? { c: '#948a82', label: 'Cancelled' }
        : { c: '#f5c451', label: 'Unconfirmed · fleet-only' }

  return (
    <section className="flex h-full flex-col border bg-card" style={{ borderColor: `${tone.c}66` }}>
      <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: `${tone.c}44`, background: `${tone.c}10` }}>
        <div className="flex items-center gap-2">
          <AlertOctagon className="size-4" style={{ color: tone.c }} />
          <h2 className="font-mono text-xs uppercase tracking-[0.18em]" style={{ color: tone.c }}>{tone.label}</h2>
        </div>
        <span className="font-mono text-[11px] uppercase" style={{ color: tone.c }}>{inc.severity}</span>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4">
        {inc.status === 'unconfirmed' && (
          <div>
            <div className="flex items-end justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Driver cancel window</span>
              <span className="font-mono text-2xl font-semibold tabular-nums" style={{ color: tone.c }}>{remaining.toFixed(1)}s</span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden bg-muted">
              <div className="h-full transition-[width] duration-100 ease-linear" style={{ width: `${pct}%`, background: tone.c }} />
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">Fleet-only until confirmed — no responder contacted yet.</p>
          </div>
        )}

        {inc.status === 'confirmed' && (
          <div className="flex items-center gap-2 border border-destructive/40 bg-destructive/10 px-3 py-2">
            <Ambulance className="size-4 text-destructive" />
            <p className="text-xs text-foreground">
              Dispatched → responder @ {inc.location.lat.toFixed(3)}, {inc.location.lon.toFixed(3)} · vehicle {inc.final_motion}
            </p>
          </div>
        )}

        <div className="grid grid-cols-3 gap-px border border-border bg-border text-center">
          {[
            { k: 'Peak Δg', v: inc.peak_g.toFixed(1) },
            { k: 'Jerk', v: inc.jerk.toFixed(0) },
            { k: 'Signals', v: `${inc.signals_fired.length}/3` },
          ].map((m) => (
            <div key={m.k} className="bg-card px-2 py-2">
              <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{m.k}</p>
              <p className="mt-0.5 text-sm font-semibold tabular-nums">{m.v}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-1.5">
          {inc.signals_fired.map((s) => (
            <span key={s} className="border border-border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{s}</span>
          ))}
        </div>

        {inc.fatigue_context.was_elevated && (
          <div className="flex items-start gap-2 border border-warning/40 bg-warning/10 px-3 py-2">
            <AlertOctagon className="mt-0.5 size-3.5 shrink-0 text-warning" />
            <p className="text-xs text-foreground">
              <span className="font-semibold text-warning">Elevated fatigue preceding crash</span> — drowsy for ~
              {Math.round(inc.fatigue_context.elevated_seconds / 60)} min (peak {Math.round(inc.fatigue_context.recent_max_score)}).
            </p>
          </div>
        )}

        <div className="mt-auto flex items-center justify-between">
          <span className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
            <MapPin className="size-3" /> {inc.location.lat.toFixed(4)}, {inc.location.lon.toFixed(4)}
          </span>
          {inc.status === 'unconfirmed' && mode === 'seeded' && (
            <Button size="sm" variant="secondary" onClick={() => liveSource.cancelCrash()}>
              <X className="size-3.5" /> Driver cancel
            </Button>
          )}
        </div>
      </div>
    </section>
  )
}
