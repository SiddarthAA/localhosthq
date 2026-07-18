import type {
  CrashCard,
  DriverState,
  DutyPoint,
  FatiguePoint,
  Kpis,
  LedgerRow,
  Level,
  RideBucket,
  Severity,
  SignalKey,
  Signals,
} from './types'

const DRIVER_ID = 'driver-1'
const DRIVER_NAME = 'Marcus Vale'
const DAY = 86_400_000

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
const rand = (a: number, b: number) => a + Math.random() * (b - a)
const sig = () => Math.random().toString(16).slice(2, 14)

const LEVELS: Level[] = ['awake', 'notice', 'warn', 'alarm']
const UP_AT = [20, 45, 72]
const DOWN_AT = [12, 38, 62]
export function levelFor(score: number, prev: Level): Level {
  let idx = LEVELS.indexOf(prev)
  while (idx < 3 && score >= UP_AT[idx]) idx++
  while (idx > 0 && score < DOWN_AT[idx - 1]) idx--
  return LEVELS[idx]
}

export function signalsFromScore(score: number): {
  signals: Signals
  fired: SignalKey[]
  agree_count: number
} {
  const t = score / 100
  const perclos = clamp(0.05 + t * 0.6 + rand(-0.04, 0.04), 0, 1)
  const head_nod = clamp(t * 0.55 + rand(-0.05, 0.05), 0, 1)
  const yawn = clamp(t * 0.4 + rand(-0.05, 0.05), 0, 1)
  const blink_dur_ms = Math.round(180 + t * 380 + rand(-20, 20))
  const blink_rate = Math.round(12 + t * 9 + rand(-1, 1))
  const ear = clamp(0.33 - t * 0.23, 0.08, 0.34)
  const fired: SignalKey[] = []
  if (perclos > 0.38) fired.push('perclos')
  if (blink_dur_ms > 400) fired.push('blink')
  if (head_nod > 0.32) fired.push('head_nod')
  if (yawn > 0.32) fired.push('yawn')
  return {
    signals: { ear, perclos, blink_rate, blink_dur_ms, head_nod, yawn },
    fired,
    agree_count: fired.length,
  }
}

/* ============================================================
   Seeded history (matches the guide: ~17 rides / 21 days / 5 incidents)
   ============================================================ */
export interface History {
  fatigue: FatiguePoint[]
  duty: DutyPoint[]
  rides: RideBucket[]
  incidents: CrashCard[]
  ledger: LedgerRow[]
  kpis: Kpis
  levelDist: { level: Level; seconds: number }[]
  signalFreq: { signal: string; count: number }[]
}

let cached: History | null = null

export function getHistory(): History {
  if (cached) return cached
  const now = Date.now()
  const fatigue: FatiguePoint[] = []
  const rideCountByDay = new Map<string, number>()
  let alerts = 0
  const levelSeconds: Record<Level, number> = { awake: 0, notice: 0, warn: 0, alarm: 0 }
  const signalTally: Record<string, number> = { perclos: 0, blink: 0, head_nod: 0, yawn: 0 }

  const RIDES = 17
  for (let r = 0; r < RIDES; r++) {
    const dayOffset = Math.floor((r / RIDES) * 21) + Math.floor(rand(0, 1.5))
    const start = now - (21 - dayOffset) * DAY - rand(0, 6 * 3_600_000)
    const dayKey = new Date(start).toISOString().slice(0, 10)
    rideCountByDay.set(dayKey, (rideCountByDay.get(dayKey) || 0) + 1)
    const session_id = `s-${r}`
    const points = 22
    // fatigue arc: mostly calm, some rides climb to warn/alarm then recover
    const peak = r % 4 === 0 ? rand(70, 88) : r % 3 === 0 ? rand(46, 66) : rand(14, 30)
    let prevLevel: Level = 'awake'
    for (let i = 0; i < points; i++) {
      const phase = i / (points - 1)
      const arc = Math.sin(phase * Math.PI) // 0..1..0
      const score = clamp(10 + arc * (peak - 10) + rand(-4, 4), 2, 96)
      const ts = start + phase * rand(30, 80) * 60_000
      const level = levelFor(score, prevLevel)
      if ((prevLevel === 'awake' || prevLevel === 'notice') && (level === 'warn' || level === 'alarm'))
        alerts++
      prevLevel = level
      fatigue.push({ ts, score, level, session_id })
      levelSeconds[level] += rand(40, 90)
      const { fired } = signalsFromScore(score)
      fired.forEach((f) => (signalTally[f] += 1))
    }
  }
  fatigue.sort((a, b) => a.ts - b.ts)

  const rides: RideBucket[] = Array.from(rideCountByDay.entries())
    .map(([day, n]) => ({ day, rides: n }))
    .sort((a, b) => a.day.localeCompare(b.day))

  // duty-cycle: a recent session's heartbeat pattern
  const duty: DutyPoint[] = []
  for (let i = 0; i < 60; i++) {
    const phase = i / 59
    const active = phase < 0.28 || (phase > 0.55 && phase < 0.72)
    const fps = active ? rand(13.5, 15) : rand(2.6, 3.6)
    duty.push({
      ts: now - (60 - i) * 5000,
      fps,
      duty: active ? 'full' : 'idle',
      speed_mps: active ? rand(9, 16) : rand(0, 3),
    })
  }

  // incidents: 2 confirmed, 3 cancelled
  const mkIncident = (
    i: number,
    status: 'confirmed' | 'cancelled',
    severity: Severity,
    elevated: boolean,
    reason?: 'driver' | 'deescalated_motion',
  ): CrashCard => {
    const detected = now - rand(1, 20) * DAY
    const win = severity === 'severe' ? 8 : 13
    return {
      incident_id: `crash-s-${i}`,
      status,
      severity,
      peak_g: severity === 'severe' ? rand(6.2, 8.5) : severity === 'moderate' ? rand(3.6, 5.9) : rand(2.5, 3.4),
      jerk: rand(180, 360),
      signals_fired: ['accel_jerk', 'gyro', ...(Math.random() > 0.4 ? ['speed_drop'] : [])],
      location: { lat: 12.93 + rand(-0.08, 0.08), lon: 77.6 + rand(-0.08, 0.08), speed_mps: status === 'confirmed' ? 0 : rand(2, 10) },
      window_seconds: win,
      cancel_window_s: win,
      fatigue_context: {
        recent_max_score: elevated ? rand(70, 86) : rand(20, 44),
        was_elevated: elevated,
        elevated_seconds: elevated ? rand(120, 340) : 0,
        sampled_over_minutes: 5,
      },
      ts_detected: detected,
      resolved_at: detected + win * 1000,
      reason: status === 'cancelled' ? reason : undefined,
      final_motion: status === 'confirmed' ? 'stopped' : undefined,
    }
  }
  const incidents: CrashCard[] = [
    mkIncident(1, 'confirmed', 'severe', true),
    mkIncident(2, 'confirmed', 'moderate', false),
    mkIncident(3, 'cancelled', 'moderate', true, 'driver'),
    mkIncident(4, 'cancelled', 'minor', false, 'driver'),
    mkIncident(5, 'cancelled', 'minor', false, 'deescalated_motion'),
  ].sort((a, b) => b.ts_detected - a.ts_detected)

  // ledger
  const ledger: LedgerRow[] = []
  const types = ['heartbeat', 'heartbeat', 'heartbeat', 'drowsiness', 'hello', 'crash']
  let prev = '0'.repeat(12)
  for (let i = 0; i < 200; i++) {
    const s = sig()
    ledger.push({
      seq: i + 1,
      type: i % 40 === 5 ? 'crash' : types[Math.floor(rand(0, 5))],
      ts: now - (200 - i) * rand(4000, 9000),
      sig: s,
      prev_sig: prev,
    })
    prev = s
  }

  const maxFatigue = Math.round(Math.max(...fatigue.map((f) => f.score)))
  const avgFatigue = Math.round(fatigue.reduce((a, f) => a + f.score, 0) / fatigue.length)

  const kpis: Kpis = {
    rides: RIDES,
    events: 2721,
    alerts,
    crashes: incidents.length,
    dispatches: incidents.filter((i) => i.status === 'confirmed').length,
    takebacks: incidents.filter((i) => i.status === 'cancelled').length,
    avgFatigue,
    maxFatigue,
  }

  const levelDist = LEVELS.map((level) => ({ level, seconds: Math.round(levelSeconds[level]) }))
  const signalFreq = Object.entries(signalTally).map(([signal, count]) => ({ signal, count }))

  cached = { fatigue, duty, rides, incidents, ledger, kpis, levelDist, signalFreq }
  return cached
}

/* ============================================================
   Live driver simulation (the demo "logic")
   ============================================================ */
type Listener = (s: DriverState) => void

export class LiveSim {
  private state: DriverState
  private listeners = new Set<Listener>()
  private timer: ReturnType<typeof setInterval> | null = null
  private drift = 0
  private naive = false
  private countdown = 0

  constructor() {
    const base = signalsFromScore(14)
    this.state = {
      driver_id: DRIVER_ID,
      name: DRIVER_NAME,
      online: true,
      session_id: 's-live',
      level: 'awake',
      score: 14,
      gated: false,
      signals: base.signals,
      fired: base.fired,
      agree_count: base.agree_count,
      duty: 'full',
      fps: 14.8,
      speed_mps: 12.5,
      calibrated: true,
      link: 'online',
      pending: 0,
      last_event_ts: Date.now(),
      updated_at: Date.now(),
      active_incident: null,
    }
  }

  get value() {
    return this.state
  }

  subscribe(cb: Listener) {
    this.listeners.add(cb)
    cb(this.state)
    if (!this.timer) this.timer = setInterval(() => this.tick(), 1200)
    return () => {
      this.listeners.delete(cb)
      if (this.listeners.size === 0 && this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
    }
  }

  private emit() {
    this.state = { ...this.state, updated_at: Date.now(), last_event_ts: Date.now() }
    this.listeners.forEach((l) => l(this.state))
  }

  private tick() {
    const s = this.state
    // countdown on an active unconfirmed incident
    if (s.active_incident && s.active_incident.status === 'unconfirmed') {
      this.countdown -= 1.2
      if (this.countdown <= 0) this.resolveCrash('confirmed')
      else this.emit()
      return
    }

    let score = s.score
    if (this.naive) {
      score = rand(35, 90) // naive spams
    } else {
      // gentle random walk toward the drift target
      const target = clamp(14 + this.drift, 6, 92)
      score += (target - score) * 0.25 + rand(-3, 3)
      this.drift *= 0.94 // decay back to calm
    }
    score = clamp(score, 3, 97)
    const level = this.naive
      ? score > 45
        ? 'alarm'
        : 'awake'
      : levelFor(score, s.level)
    const sig = signalsFromScore(score)
    const speed = clamp(s.speed_mps + rand(-1.5, 1.5), 0, 22)
    const gated = speed < 1.2
    const calm = level === 'awake'
    const duty = calm ? 'idle' : 'full'
    this.state = {
      ...s,
      score,
      level: gated ? 'awake' : level,
      gated,
      signals: sig.signals,
      fired: gated ? [] : sig.fired,
      agree_count: gated ? 0 : sig.agree_count,
      duty,
      fps: duty === 'full' ? rand(13.5, 15) : rand(2.6, 3.6),
      speed_mps: speed,
      link: 'online',
      pending: 0,
    }
    this.emit()
  }

  /** demo: push the driver toward drowsiness (the graduated climb) */
  pushDrowsy() {
    this.drift = 80
    this.emit()
  }

  setNaive(on: boolean) {
    this.naive = on
    if (!on) this.drift = 0
    this.emit()
  }

  triggerCrash(severity: Severity = 'severe') {
    const win = severity === 'severe' ? 8 : 13
    this.countdown = win
    const elevated = this.state.score > 55
    this.state = {
      ...this.state,
      active_incident: {
        incident_id: `crash-live-${Date.now()}`,
        status: 'unconfirmed',
        severity,
        peak_g: severity === 'severe' ? 7.4 : 4.8,
        jerk: 312,
        signals_fired: ['accel_jerk', 'gyro', 'speed_drop'],
        location: { lat: 12.9716, lon: 77.5946, speed_mps: 0 },
        window_seconds: win,
        cancel_window_s: win,
        fatigue_context: {
          recent_max_score: Math.round(this.state.score),
          was_elevated: elevated,
          elevated_seconds: elevated ? 210 : 0,
          sampled_over_minutes: 5,
        },
        ts_detected: Date.now(),
      },
    }
    this.emit()
  }

  cancelCrash() {
    this.resolveCrash('cancelled', 'driver')
  }

  private resolveCrash(status: 'confirmed' | 'cancelled', reason?: 'driver') {
    const inc = this.state.active_incident
    if (!inc) return
    this.state = {
      ...this.state,
      active_incident: {
        ...inc,
        status,
        resolved_at: Date.now(),
        reason: status === 'cancelled' ? reason : undefined,
        final_motion: status === 'confirmed' ? 'stopped' : undefined,
      },
    }
    this.emit()
    // clear the card a few seconds after resolution
    setTimeout(() => {
      if (this.state.active_incident?.incident_id === inc.incident_id) {
        this.state = { ...this.state, active_incident: null }
        this.emit()
      }
    }, 6000)
  }
}

export const liveSim = new LiveSim()
