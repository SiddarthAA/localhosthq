import { BellRing, ShieldCheck } from 'lucide-react'
import Panel from './Panel'
import { useAlerts } from '@/lib/hooks'
import type { AlertItem } from '@/lib/types'

const TONE: Record<AlertItem['tone'], string> = { warn: '#f5c451', alert: '#ff5148', ok: '#6fe0c4' }
const fmt = (ts: number) =>
  new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

export default function AlertsLog() {
  const alerts = useAlerts()
  return (
    <Panel
      title="Alerts"
      icon={<BellRing className="size-4 text-primary" />}
      right={<span className="font-mono text-[11px] text-muted-foreground">{alerts.length} this session</span>}
      bodyClass=""
    >
      {alerts.length === 0 ? (
        <div className="flex items-center gap-2 px-4 py-6 text-xs text-muted-foreground">
          <ShieldCheck className="size-4 text-primary" />
          No alerts yet — drowsiness alarms, crashes and dispatches land here.
        </div>
      ) : (
        <div className="max-h-[220px] divide-y divide-border overflow-y-auto">
          {alerts.map((a) => (
            <div key={a.id} className="flex items-start gap-3 px-4 py-2.5">
              <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: TONE[a.tone] }} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold" style={{ color: TONE[a.tone] }}>
                  {a.title}
                </p>
                <p className="truncate font-mono text-[10px] text-muted-foreground">{a.detail}</p>
              </div>
              <span className="shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground">{fmt(a.ts)}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}
