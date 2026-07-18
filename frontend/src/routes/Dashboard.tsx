import TopBar from '@/components/dashboard/TopBar'
import Kpis from '@/components/dashboard/Kpis'
import LivePanel from '@/components/dashboard/LivePanel'
import CrashPanel from '@/components/dashboard/CrashPanel'
import Incidents from '@/components/dashboard/Incidents'
import Ledger from '@/components/dashboard/Ledger'
import {
  DutyCycleChart,
  FatigueTimeline,
  LevelDistribution,
  RidesPerDay,
  SignalFrequency,
} from '@/components/dashboard/Charts'

const wide = { fontVariationSettings: '"wdth" 120' } as const

export default function Dashboard() {
  return (
    <div className="min-h-svh bg-background font-sans text-foreground">
      <TopBar />
      <main className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold" style={wide}>
              Fleet overview
            </h1>
            <p className="font-mono text-[11px] text-muted-foreground">
              Single active driver · decisions only — no video, no raw sensors leave the edge
            </p>
          </div>
          <span className="border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            demo · seeded history
          </span>
        </div>

        {/* hero row */}
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LivePanel />
          </div>
          <CrashPanel />
        </div>

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
