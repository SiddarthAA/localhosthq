import {
  Activity,
  BarChart3,
  Cpu,
  Layers,
  TrendingUp,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { getHistory } from '@/lib/data'
import { LEVEL_LABEL, type Level } from '@/lib/types'
import Panel from './Panel'

const axisTick = { fill: 'var(--muted-foreground)', fontSize: 10, fontFamily: 'var(--font-mono)' }
const LEVEL_HEX: Record<Level, string> = { awake: '#6fe0c4', notice: '#7c9cff', warn: '#f5c451', alarm: '#ff5148' }

const fmtDay = (ts: number) =>
  new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

export function FatigueTimeline() {
  const { fatigue } = getHistory()
  const data = fatigue.filter((_, i) => i % 2 === 0).map((f) => ({ ts: f.ts, score: Math.round(f.score) }))
  const config = { score: { label: 'Fatigue', color: 'var(--chart-1)' } } satisfies ChartConfig
  return (
    <Panel title="Fatigue score · 21-day history" icon={<TrendingUp className="size-4 text-primary" />}>
      <ChartContainer config={config} className="h-[220px] w-full">
        <AreaChart data={data} margin={{ top: 6, right: 8, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="fatFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.5} />
          <XAxis dataKey="ts" tickFormatter={fmtDay} tick={axisTick} tickLine={false} axisLine={false} minTickGap={60} />
          <YAxis domain={[0, 100]} tick={axisTick} tickLine={false} axisLine={false} width={38} />
          <ReferenceLine y={72} stroke="#ff5148" strokeDasharray="3 3" strokeOpacity={0.5} />
          <ReferenceLine y={45} stroke="#f5c451" strokeDasharray="3 3" strokeOpacity={0.5} />
          <ChartTooltip content={<ChartTooltipContent labelFormatter={(_, p) => fmtDay(p?.[0]?.payload?.ts)} />} />
          <Area type="monotone" dataKey="score" stroke="var(--chart-1)" strokeWidth={1.6} fill="url(#fatFill)" isAnimationActive={false} />
        </AreaChart>
      </ChartContainer>
    </Panel>
  )
}

export function DutyCycleChart() {
  const { duty } = getHistory()
  const data = duty.map((d, i) => ({ i, fps: Number(d.fps.toFixed(1)) }))
  const config = { fps: { label: 'FPS', color: 'var(--chart-1)' } } satisfies ChartConfig
  return (
    <Panel title="Adaptive duty-cycle · inference fps" icon={<Cpu className="size-4 text-primary" />}>
      <ChartContainer config={config} className="h-[180px] w-full">
        <AreaChart data={data} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="dutyFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.5} />
          <YAxis domain={[0, 16]} tick={axisTick} tickLine={false} axisLine={false} width={34} />
          <XAxis dataKey="i" hide />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Area type="stepAfter" dataKey="fps" stroke="var(--chart-1)" strokeWidth={2} fill="url(#dutyFill)" isAnimationActive={false} />
        </AreaChart>
      </ChartContainer>
      <p className="mt-2 font-mono text-[10px] text-muted-foreground">Holds ~15 fps when alert · drops to ~3 fps when calm · snaps back instantly.</p>
    </Panel>
  )
}

export function LevelDistribution() {
  const { levelDist } = getHistory()
  const total = levelDist.reduce((a, l) => a + l.seconds, 0)
  const data = levelDist.map((l) => ({ name: LEVEL_LABEL[l.level], value: l.seconds, level: l.level }))
  return (
    <Panel title="Time by alert level" icon={<Layers className="size-4 text-primary" />}>
      <div className="flex items-center gap-4">
        <ChartContainer config={{}} className="h-[150px] w-[150px] shrink-0">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={44} outerRadius={64} paddingAngle={2} strokeWidth={0}>
              {data.map((d) => (
                <Cell key={d.level} fill={LEVEL_HEX[d.level]} />
              ))}
            </Pie>
            <ChartTooltip content={<ChartTooltipContent />} />
          </PieChart>
        </ChartContainer>
        <div className="flex-1 space-y-2">
          {data.map((d) => (
            <div key={d.level} className="flex items-center gap-2 text-xs">
              <span className="size-2.5" style={{ background: LEVEL_HEX[d.level] }} />
              <span className="flex-1">{d.name}</span>
              <span className="font-mono tabular-nums text-muted-foreground">{Math.round((d.value / total) * 100)}%</span>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  )
}

export function SignalFrequency() {
  const { signalFreq } = getHistory()
  const data = signalFreq
    .map((s) => ({ signal: s.signal.replace('_', ' '), count: s.count }))
    .sort((a, b) => b.count - a.count)
  const config = { count: { label: 'Fired', color: 'var(--chart-1)' } } satisfies ChartConfig
  return (
    <Panel title="Signals fired · frequency" icon={<Activity className="size-4 text-primary" />}>
      <ChartContainer config={config} className="h-[180px] w-full">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid horizontal={false} stroke="var(--border)" strokeOpacity={0.5} />
          <XAxis type="number" tick={axisTick} tickLine={false} axisLine={false} />
          <YAxis type="category" dataKey="signal" tick={axisTick} tickLine={false} axisLine={false} width={70} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="count" fill="var(--chart-1)" radius={0} barSize={16} />
        </BarChart>
      </ChartContainer>
    </Panel>
  )
}

export function RidesPerDay() {
  const { rides } = getHistory()
  const data = rides.map((r) => ({ day: fmtDay(new Date(r.day).getTime()), rides: r.rides }))
  const config = { rides: { label: 'Rides', color: 'var(--chart-2)' } } satisfies ChartConfig
  return (
    <Panel title="Rides per day" icon={<BarChart3 className="size-4 text-primary" />}>
      <ChartContainer config={config} className="h-[180px] w-full">
        <BarChart data={data} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.5} />
          <XAxis dataKey="day" tick={axisTick} tickLine={false} axisLine={false} minTickGap={20} />
          <YAxis allowDecimals={false} tick={axisTick} tickLine={false} axisLine={false} width={30} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="rides" fill="var(--chart-2)" radius={0} barSize={18} />
        </BarChart>
      </ChartContainer>
    </Panel>
  )
}
