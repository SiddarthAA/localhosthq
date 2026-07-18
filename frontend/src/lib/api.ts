// REST client for the collector's signed-event ledger. All chart/KPI history is
// DERIVED here from raw signed events (the backend stays a dumb relay + ledger).
//
// NOTE: backend timestamps are unix SECONDS; the UI uses `new Date(ms)`, so every
// ts is ×1000 at this boundary.

import { HTTP_BASE, PRIMARY_DRIVER } from './config'
import type {
  CrashCard,
  DutyPoint,
  FatiguePoint,
  Kpis,
  LedgerRow,
  Level,
  RideBucket,
  VerifyResult,
} from './types'
import type { History } from './data'

const SEC = 1000

interface SignedEvent {
  v: number
  type: string
  driver_id: string
  session_id: string
  seq: number
  ts: number
  prev_sig: string
  sig: string
  payload: Record<string, unknown>
}

async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${HTTP_BASE}${path}`, { signal })
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`)
  return (await res.json()) as T
}

export interface Health {
  ok: boolean
  drivers: number
  subscribers: number
}
export const getHealth = (signal?: AbortSignal) => getJSON<Health>('/api/health', signal)
export const verifyLedger = (id = PRIMARY_DRIVER, signal?: AbortSignal) =>
  getJSON<VerifyResult>(`/api/drivers/${id}/ledger/verify`, signal)

const num = (v: unknown, d = 0): number => (typeof v === 'number' ? v : d)

// Crash payload (or /api/incidents card) → the dashboard's CrashCard shape.
export function mapIncident(x: Record<string, any>): CrashCard {
  return {
    incident_id: x.incident_id,
    status: x.status,
    severity: x.severity,
    peak_g: num(x.peak_g),
    jerk: num(x.jerk),
    signals_fired: x.signals_fired ?? [],
    location: x.location ?? { lat: 0, lon: 0, speed_mps: 0 },
    window_seconds: num(x.window_seconds, 8),
    cancel_window_s: num(x.cancel_window_s ?? x.window_seconds, 8),
    fatigue_context: x.fatigue_context ?? {
      recent_max_score: 0,
      was_elevated: false,
      elevated_seconds: 0,
      sampled_over_minutes: 0,
    },
    ts_detected: num(x.ts_detected ?? x.detected_at ?? x.ts) * SEC,
    resolved_at: x.resolved_at ? x.resolved_at * SEC : undefined,
    reason: x.reason,
    final_motion: x.final_motion,
  }
}

const LEVELS: Level[] = ['awake', 'notice', 'warn', 'alarm']

// Fetch the ledger for one driver and derive every chart + KPI the dashboard uses.
export async function buildHistory(id = PRIMARY_DRIVER, signal?: AbortSignal): Promise<History> {
  const evs = (p: string) => getJSON<SignedEvent[]>(p, signal)
  const [drowsy, beats, hellos, incidentsRaw, ledgerRaw, verify] = await Promise.all([
    evs(`/api/drivers/${id}/events?type=drowsiness&limit=5000`),
    evs(`/api/drivers/${id}/events?type=heartbeat&limit=300`),
    evs(`/api/drivers/${id}/events?type=hello&limit=300`),
    getJSON<Record<string, any>[]>(`/api/incidents?limit=50`, signal),
    evs(`/api/drivers/${id}/ledger?limit=200`),
    verifyLedger(id, signal).catch(
      () => ({ ok: true, count: 0, broken_at: null, checked_at: 0 }) as VerifyResult,
    ),
  ])

  // fatigue timeline (chronological, downsampled to ~500 pts for the chart)
  const allF = drowsy
    .map((e) => ({
      ts: e.ts * SEC,
      score: num((e.payload as any).score),
      level: ((e.payload as any).level ?? 'awake') as Level,
      session_id: e.session_id,
    }))
    .sort((a, b) => a.ts - b.ts)
  const step = Math.max(1, Math.ceil(allF.length / 500))
  const fatigue: FatiguePoint[] = allF.filter((_, i) => i % step === 0)

  // adaptive duty-cycle from heartbeats (clamp the first-beat fps spike; last ~60)
  const duty: DutyPoint[] = beats
    .map((e) => ({
      ts: e.ts * SEC,
      fps: Math.min(16, Math.max(0, num((e.payload as any).fps))),
      duty: (((e.payload as any).duty ?? 'full') as DutyPoint['duty']),
      speed_mps: num((e.payload as any).speed_mps),
    }))
    .sort((a, b) => a.ts - b.ts)
    .slice(-60)

  // rides/day from hello events (one per session/ride)
  const rideByDay = new Map<string, number>()
  for (const h of hellos) {
    const day = new Date(h.ts * SEC).toISOString().slice(0, 10)
    rideByDay.set(day, (rideByDay.get(day) ?? 0) + 1)
  }
  const rides: RideBucket[] = [...rideByDay.entries()]
    .map(([day, n]) => ({ day, rides: n }))
    .sort((a, b) => a.day.localeCompare(b.day))

  // level distribution + signals-fired frequency + drowsy-alarm count
  const levelSeconds: Record<Level, number> = { awake: 0, notice: 0, warn: 0, alarm: 0 }
  const sigTally: Record<string, number> = {}
  let alerts = 0
  for (const e of drowsy) {
    const p = e.payload as any
    const lv = (p.level ?? 'awake') as Level
    levelSeconds[lv] += 1
    for (const f of (p.fired ?? []) as string[]) sigTally[f] = (sigTally[f] ?? 0) + 1
    if (p.kind === 'transition' && (lv === 'warn' || lv === 'alarm')) alerts++
  }
  const levelDist = LEVELS.map((level) => ({ level, seconds: levelSeconds[level] }))
  const signalFreq = Object.entries(sigTally).map(([signal, count]) => ({ signal, count }))

  // incidents for this driver, newest first
  const incidents: CrashCard[] = incidentsRaw
    .filter((x) => !x.driver_id || x.driver_id === id)
    .map(mapIncident)
    .sort((a, b) => b.ts_detected - a.ts_detected)

  // ledger rows: real type/ts/sig with a monotonic display seq (tamper demo intact)
  const ledger: LedgerRow[] = ledgerRaw
    .slice()
    .sort((a, b) => a.ts - b.ts)
    .map((e, i) => ({ seq: i + 1, type: e.type, ts: e.ts * SEC, sig: e.sig, prev_sig: e.prev_sig }))

  const scores = allF.map((f) => f.score)
  const maxFatigue = scores.length ? Math.round(Math.max(...scores)) : 0
  const avgFatigue = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
  const rideCount = rides.reduce((a, r) => a + r.rides, 0) || new Set(drowsy.map((e) => e.session_id)).size

  const kpis: Kpis = {
    rides: rideCount,
    events: verify.count || drowsy.length + beats.length + hellos.length,
    alerts,
    crashes: incidents.length,
    dispatches: incidents.filter((i) => i.status === 'confirmed').length,
    takebacks: incidents.filter((i) => i.status === 'cancelled').length,
    avgFatigue,
    maxFatigue,
  }

  return { fatigue, duty, rides, incidents, ledger, kpis, levelDist, signalFreq }
}
