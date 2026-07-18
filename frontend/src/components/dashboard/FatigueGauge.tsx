import type { Level } from '@/lib/types'
import { LEVEL_LABEL } from '@/lib/types'

const START = -120
const SWEEP = 240
const R = 84
const CX = 100
const CY = 100

function polar(deg: number, r = R) {
  const a = ((deg - 90) * Math.PI) / 180
  return [CX + r * Math.cos(a), CY + r * Math.sin(a)] as const
}
function arc(startDeg: number, endDeg: number, r = R) {
  const [x0, y0] = polar(startDeg, r)
  const [x1, y1] = polar(endDeg, r)
  const large = endDeg - startDeg <= 180 ? 0 : 1
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`
}

const LEVEL_HEX: Record<Level, string> = {
  awake: '#6fe0c4',
  notice: '#7c9cff',
  warn: '#f5c451',
  alarm: '#ff5148',
}

export default function FatigueGauge({
  score,
  level,
  gated,
}: {
  score: number
  level: Level
  gated: boolean
}) {
  const valDeg = START + (score / 100) * SWEEP
  const color = gated ? '#948a82' : LEVEL_HEX[level]
  // threshold ticks at 20 / 45 / 72
  const ticks = [20, 45, 72]

  return (
    <div className="relative flex flex-col items-center">
      <svg viewBox="0 0 200 170" className="w-full max-w-[280px]">
        <path d={arc(START, START + SWEEP)} fill="none" stroke="var(--border)" strokeWidth="10" strokeLinecap="round" />
        <path
          d={arc(START, valDeg)}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${color}66)`, transition: 'all 0.6s cubic-bezier(0.22,1,0.36,1)' }}
        />
        {ticks.map((t) => {
          const [x, y] = polar(START + (t / 100) * SWEEP, R + 9)
          const [x2, y2] = polar(START + (t / 100) * SWEEP, R + 2)
          return <line key={t} x1={x} y1={y} x2={x2} y2={y2} stroke="var(--muted-foreground)" strokeWidth="1.5" opacity="0.5" />
        })}
        <text x={CX} y={CY - 4} textAnchor="middle" className="fill-foreground" style={{ fontSize: 40, fontWeight: 600, fontVariationSettings: '"wdth" 120' }}>
          {Math.round(score)}
        </text>
        <text x={CX} y={CY + 18} textAnchor="middle" className="fill-muted-foreground font-mono" style={{ fontSize: 9, letterSpacing: 2 }}>
          FATIGUE
        </text>
      </svg>
      <div
        className="-mt-3 inline-flex items-center gap-1.5 border px-2.5 py-1"
        style={{ borderColor: `${color}66`, background: `${color}14` }}
      >
        <span className="size-1.5 rounded-full" style={{ background: color }} />
        <span className="font-mono text-[11px] uppercase tracking-[0.15em]" style={{ color }}>
          {gated ? 'Parked · monitoring' : LEVEL_LABEL[level]}
        </span>
      </div>
    </div>
  )
}
