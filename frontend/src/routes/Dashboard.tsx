import TopBar from '@/components/dashboard/TopBar'
import Kpis from '@/components/dashboard/Kpis'
import LivePanel from '@/components/dashboard/LivePanel'
import CrashPanel from '@/components/dashboard/CrashPanel'
import AlertsLog from '@/components/dashboard/AlertsLog'
import Incidents from '@/components/dashboard/Incidents'
import Ledger from '@/components/dashboard/Ledger'
import {
  DutyCycleChart,
  FatigueTimeline,
  LevelDistribution,
  RidesPerDay,
  SignalFrequency,
} from '@/components/dashboard/Charts'
import { Volume2, VolumeX } from 'lucide-react'
import { Toaster } from '@/components/ui/sonner'
import { useConn, useMode, useMuted } from '@/lib/hooks'
import type { Mode } from '@/lib/types'

const wide = { fontVariationSettings: '"wdth" 120' } as const

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: 'live', label: 'Live', hint: 'full edge stream' },
  { id: 'alerts', label: 'Alerts', hint: 'alerts only' },
  { id: 'seeded', label: 'Seeded', hint: 'offline demo' },
]

function ModeBar() {
  const [mode, setMode] = useMode()
  const conn = useConn()
  const [muted, toggleMuted] = useMuted()
  const connColor =
    mode === 'seeded' ? '#948a82' : conn === 'online' ? '#6fe0c4' : conn === 'connecting' ? '#f5c451' : '#ff5148'
  const connLabel = mode === 'seeded' ? 'offline demo' : conn === 'online' ? 'edge connected' : conn

  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        <span className="size-2 rounded-full" style={{ background: connColor }} />
        {connLabel}
      </span>
      <div className="flex border border-border" role="group" aria-label="Data mode">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            title={m.hint}
            aria-pressed={mode === m.id}
            className={`px-3 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors ${
              mode === m.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary/60'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={toggleMuted}
        aria-pressed={!muted}
        title={muted ? 'Alert chimes off — click to enable' : 'Alert chimes on'}
        className="border border-border p-1.5 text-muted-foreground transition-colors hover:bg-secondary/60"
      >
        {muted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5 text-primary" />}
      </button>
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="min-h-svh bg-background font-sans text-foreground">
      <Toaster position="top-right" />
      <TopBar />
      <main className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold" style={wide}>
              Fleet overview
            </h1>
            <p className="font-mono text-[11px] text-muted-foreground">
              Single active driver · decisions only — no video, no raw sensors leave the edge
            </p>
          </div>
          <ModeBar />
        </div>

        {/* hero row */}
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LivePanel />
          </div>
          <CrashPanel />
        </div>

        <AlertsLog />

        <Kpis />

        <FatigueTimeline />

        <div className="grid gap-4 lg:grid-cols-3">
          <DutyCycleChart />
          <LevelDistribution />
          <SignalFrequency />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <RidesPerDay />
          <Incidents />
        </div>

        <Ledger />

        <p className="pt-2 text-center font-mono text-[10px] text-muted-foreground/60">
          RidewMe fleet console · charts from signed REST history · live tile from the edge daemon (WS)
        </p>
      </main>
    </div>
  )
}
