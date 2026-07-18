import { useHistory } from '@/lib/hooks'

export default function Kpis() {
  const { kpis } = useHistory()
  const items = [
    { k: 'Rides', v: kpis.rides, sub: 'last 21 days' },
    { k: 'Events', v: kpis.events.toLocaleString(), sub: 'signed' },
    { k: 'Drowsy alerts', v: kpis.alerts, sub: 'warn + alarm', tone: 'warn' as const },
    { k: 'Crashes', v: kpis.crashes, sub: 'detected' },
    { k: 'Dispatches', v: kpis.dispatches, sub: 'confirmed', tone: 'alert' as const },
    { k: 'Take-backs', v: kpis.takebacks, sub: 'cancelled' },
    { k: 'Avg fatigue', v: kpis.avgFatigue, sub: 'per ride' },
    { k: 'Peak fatigue', v: kpis.maxFatigue, sub: 'max score' },
  ]
  return (
    <div className="grid grid-cols-2 gap-px border border-border bg-border sm:grid-cols-4 xl:grid-cols-8">
      {items.map((it) => (
        <div key={it.k} className="bg-card px-4 py-3.5">
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{it.k}</p>
          <p
            className="mt-1 text-2xl font-semibold tabular-nums"
            style={{
              fontVariationSettings: '"wdth" 118',
              color: it.tone === 'alert' ? 'var(--destructive)' : it.tone === 'warn' ? 'var(--warning)' : undefined,
            }}
          >
            {it.v}
          </p>
          <p className="mt-0.5 font-mono text-[10px] text-muted-foreground/70">{it.sub}</p>
        </div>
      ))}
    </div>
  )
}
