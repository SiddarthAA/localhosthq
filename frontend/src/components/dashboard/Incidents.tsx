import { AlertTriangle, ChevronRight } from 'lucide-react'
import { getHistory } from '@/lib/data'
import type { Severity } from '@/lib/types'
import Panel from './Panel'

const SEV_HEX: Record<Severity, string> = { minor: '#6fe0c4', moderate: '#f5c451', severe: '#ff5148' }
const fmt = (ts: number) => new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

export default function Incidents() {
  const { incidents } = getHistory()
  const confirmed = incidents.filter((i) => i.status === 'confirmed').length
  return (
    <Panel
      title="Incident history"
      icon={<AlertTriangle className="size-4 text-primary" />}
      right={
        <span className="font-mono text-[11px] text-muted-foreground">
          <span className="text-destructive">{confirmed}</span> dispatched · {incidents.length - confirmed} cancelled
        </span>
      }
      bodyClass=""
    >
      <div className="divide-y divide-border">
        {incidents.map((inc) => {
          const c = SEV_HEX[inc.severity]
          return (
            <div key={inc.incident_id} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-secondary/60">
              <span className="size-2 shrink-0" style={{ background: c }} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold capitalize">{inc.severity}</span>
                  <span
                    className="border px-1.5 py-px font-mono text-[9px] uppercase tracking-wider"
                    style={
                      inc.status === 'confirmed'
                        ? { color: '#ff5148', borderColor: '#ff514855' }
                        : { color: 'var(--muted-foreground)', borderColor: 'var(--border)' }
                    }
                  >
                    {inc.status === 'confirmed' ? 'dispatched' : inc.reason === 'driver' ? 'driver cancel' : 'de-escalated'}
                  </span>
                  {inc.fatigue_context.was_elevated && (
                    <span className="border border-warning/40 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-warning">
                      fatigue↑
                    </span>
                  )}
                </div>
                <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                  {fmt(inc.ts_detected)} · peak {inc.peak_g.toFixed(1)}g · {inc.signals_fired.length}/3 signals
                </p>
              </div>
              <ChevronRight className="size-4 shrink-0 text-muted-foreground/50" />
            </div>
          )
        })}
      </div>
    </Panel>
  )
}
