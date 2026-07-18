import { useState } from 'react'
import { ShieldAlert, ShieldCheck, FileWarning } from 'lucide-react'
import { getHistory } from '@/lib/data'
import Panel from './Panel'
import { Button } from '@/components/ui/button'

const BROKEN_AT = 137
const fmtT = (ts: number) => new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

export default function Ledger() {
  const { ledger, kpis } = getHistory()
  const [tampered, setTampered] = useState(false)
  const rows = [...ledger].reverse()

  return (
    <Panel
      title="Signed event ledger"
      icon={<FileWarning className="size-4 text-primary" />}
      right={
        <Button size="sm" variant={tampered ? 'secondary' : 'outline'} onClick={() => setTampered((t) => !t)}>
          {tampered ? 'Restore chain' : 'Tamper a row'}
        </Button>
      }
      bodyClass=""
    >
      {/* verify badge */}
      <div className="mx-4 mt-4 flex items-center gap-3 border p-3" style={tampered ? { borderColor: '#ff514855', background: '#ff51480d' } : { borderColor: '#6fe0c455', background: '#6fe0c40d' }}>
        {tampered ? <ShieldAlert className="size-5 text-destructive" /> : <ShieldCheck className="size-5 text-primary" />}
        <div>
          <p className="text-sm font-semibold" style={{ color: tampered ? '#ff5148' : '#6fe0c4' }}>
            {tampered ? 'Tamper detected' : 'Chain verified'}
          </p>
          <p className="font-mono text-[10px] text-muted-foreground">
            {tampered ? `Ed25519 broken at seq #${BROKEN_AT}` : `${kpis.events.toLocaleString()} events · Ed25519 signed chain`}
          </p>
        </div>
        <span className="ml-auto font-mono text-[10px] uppercase tracking-wider" style={{ color: tampered ? '#ff5148' : '#6fe0c4' }}>
          ledger/verify → {tampered ? 'ok:false' : 'ok:true'}
        </span>
      </div>

      {/* rows */}
      <div className="mt-3 max-h-[280px] overflow-y-auto">
        <table className="w-full text-left">
          <thead className="sticky top-0 bg-card">
            <tr className="border-y border-border font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-2 font-medium">Seq</th>
              <th className="py-2 font-medium">Type</th>
              <th className="py-2 font-medium">Time</th>
              <th className="px-4 py-2 text-right font-medium">Sig</th>
            </tr>
          </thead>
          <tbody className="font-mono text-[11px]">
            {rows.map((r) => {
              const broken = tampered && r.seq >= BROKEN_AT
              return (
                <tr key={r.seq} className={broken ? 'bg-destructive/10 text-destructive' : 'text-foreground/80'}>
                  <td className="px-4 py-1.5 tabular-nums text-muted-foreground">#{r.seq}</td>
                  <td className="py-1.5">{r.type}</td>
                  <td className="py-1.5 tabular-nums text-muted-foreground">{fmtT(r.ts)}</td>
                  <td className="px-4 py-1.5 text-right tabular-nums text-muted-foreground">{r.sig.slice(0, 8)}…</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
