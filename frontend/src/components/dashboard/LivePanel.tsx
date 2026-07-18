import { useEffect, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, YAxis } from 'recharts'
import { AlertTriangle, Gauge, Zap } from 'lucide-react'
import { useLive } from '@/lib/useLive'
import { liveSource } from '@/lib/fleet'
import { useMode } from '@/lib/hooks'
import type { DriverState, SignalKey } from '@/lib/types'
import FatigueGauge from './FatigueGauge'
import { Button } from '@/components/ui/button'

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

const SIGS: { key: SignalKey; label: string; read: (s: DriverState) => string; frac: (s: DriverState) => number }[] = [
  { key: 'perclos', label: 'PERCLOS', read: (s) => `${Math.round(s.signals.perclos * 100)}%`, frac: (s) => s.signals.perclos },
  { key: 'blink', label: 'Blink dur', read: (s) => `${Math.round(s.signals.blink_dur_ms)}ms`, frac: (s) => clamp01((s.signals.blink_dur_ms - 150) / 450) },
  { key: 'head_nod', label: 'Head nod', read: (s) => s.signals.head_nod.toFixed(2), frac: (s) => s.signals.head_nod },
  { key: 'yawn', label: 'Yawn', read: (s) => s.signals.yawn.toFixed(2), frac: (s) => s.signals.yawn },
]

export default function LivePanel() {
  const d = useLive()
  const [mode] = useMode()
  const [buf, setBuf] = useState<{ i: number; score: number }[]>([])
  const [naive, setNaive] = useState(false)

  useEffect(() => {
    setBuf((b) => [...b, { i: (b.at(-1)?.i ?? 0) + 1, score: Math.round(d.score) }].slice(-46))
  }, [d.updated_at, d.score])

  return (
    <section className="border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Gauge className="size-4 text-primary" />
          <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Live driver · fatigue decision
          </h2>
        </div>
        <span className="font-mono text-[11px] text-muted-foreground">
          {d.calibrated ? 'baseline locked' : 'learning baseline…'}
        </span>
      </div>

      <div className="grid gap-6 p-5 lg:grid-cols-[minmax(0,300px)_1fr]">
        {/* gauge */}
        <div className="flex flex-col items-center justify-center gap-4">
          <FatigueGauge score={d.score} level={d.level} gated={d.gated} />
          <div className="grid w-full grid-cols-3 gap-px border border-border bg-border text-center">
            {[
              { k: 'Speed', v: `${(d.speed_mps * 3.6).toFixed(0)} km/h` },
              { k: 'Inference', v: `${d.fps.toFixed(1)} fps` },
              { k: 'Duty', v: d.duty },
            ].map((m) => (
              <div key={m.k} className="bg-card px-2 py-2">
                <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{m.k}</p>
                <p className="mt-0.5 text-sm font-semibold tabular-nums">{m.v}</p>
              </div>
            ))}
          </div>
        </div>

        {/* right: sparkline + signals + controls */}
        <div className="flex flex-col gap-5">
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Fatigue score · live</span>
              <span className="font-mono text-[10px] text-muted-foreground">last ~1 min</span>
            </div>
            <div className="h-[70px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={buf} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <YAxis domain={[0, 100]} hide />
                  <Area type="monotone" dataKey="score" stroke="var(--chart-1)" strokeWidth={2} fill="url(#spark)" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* signals */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Signals</span>
              <span className="font-mono text-[10px]">
                <span className={d.agree_count >= 2 ? 'text-warning' : 'text-muted-foreground'}>{d.agree_count}</span>
                <span className="text-muted-foreground"> / 2 to alarm</span>
              </span>
            </div>
            {SIGS.map((sg) => {
              const fired = d.fired.includes(sg.key)
              const frac = clamp01(sg.frac(d))
              return (
                <div key={sg.key} className="flex items-center gap-3">
                  <span className={`w-16 shrink-0 font-mono text-[10px] uppercase ${fired ? 'text-warning' : 'text-muted-foreground'}`}>{sg.label}</span>
                  <div className="h-1.5 flex-1 overflow-hidden bg-muted">
                    <div
                      className="h-full transition-all duration-500"
                      style={{ width: `${frac * 100}%`, background: fired ? 'var(--warning)' : 'var(--chart-1)', opacity: fired ? 1 : 0.55 }}
                    />
                  </div>
                  <span className="w-12 shrink-0 text-right font-mono text-[10px] tabular-nums text-muted-foreground">{sg.read(d)}</span>
                </div>
              )
            })}
          </div>

          {/* demo controls — only in the offline seeded demo; real driver drives live/alerts */}
          {mode === 'seeded' ? (
            <div className="flex flex-wrap gap-2 border-t border-border pt-4">
              <Button size="sm" variant="secondary" onClick={() => liveSource.pushDrowsy()}>
                <Zap className="size-3.5" /> Simulate drowsiness
              </Button>
              <Button size="sm" variant="secondary" onClick={() => liveSource.triggerCrash('severe')}>
                <AlertTriangle className="size-3.5" /> Trigger crash
              </Button>
              <Button
                size="sm"
                variant={naive ? 'destructive' : 'outline'}
                onClick={() => { const n = !naive; setNaive(n); liveSource.setNaive(n) }}
              >
                {naive ? 'Naive: ON (spams)' : 'Naive mode'}
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 border-t border-border pt-4 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              <span className="size-1.5 rounded-full" style={{ background: mode === 'alerts' ? '#f5c451' : '#6fe0c4' }} />
              {mode === 'alerts' ? 'alerts-only · live telemetry paused' : 'live from edge daemon'}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
