export type Level = 'awake' | 'notice' | 'warn' | 'alarm'
export type Duty = 'full' | 'idle'
export type Link = 'online' | 'degraded' | 'offline'
export type Severity = 'minor' | 'moderate' | 'severe'
export type CrashStatus = 'unconfirmed' | 'confirmed' | 'cancelled'
export type SignalKey = 'perclos' | 'blink' | 'head_nod' | 'yawn'

export interface Signals {
  ear: number
  perclos: number
  blink_rate: number
  blink_dur_ms: number
  head_nod: number
  yawn: number
}

export interface CrashCard {
  incident_id: string
  status: CrashStatus
  severity: Severity
  peak_g: number
  jerk: number
  signals_fired: string[]
  location: { lat: number; lon: number; speed_mps: number }
  window_seconds: number
  cancel_window_s: number
  fatigue_context: {
    recent_max_score: number
    was_elevated: boolean
    elevated_seconds: number
    sampled_over_minutes: number
  }
  ts_detected: number
  resolved_at?: number
  reason?: 'driver' | 'deescalated_motion'
  final_motion?: 'stopped' | 'moving'
}

export interface DriverState {
  driver_id: string
  name: string
  online: boolean
  session_id: string
  level: Level
  score: number
  gated: boolean
  signals: Signals
  fired: SignalKey[]
  agree_count: number
  duty: Duty
  fps: number
  speed_mps: number
  calibrated: boolean
  link: Link
  pending: number
  last_event_ts: number
  updated_at: number
  active_incident: CrashCard | null
}

export interface FatiguePoint {
  ts: number
  score: number
  level: Level
  session_id: string
}

export interface DutyPoint {
  ts: number
  fps: number
  duty: Duty
  speed_mps: number
}

export interface LedgerRow {
  seq: number
  type: string
  ts: number
  sig: string
  prev_sig: string
  tampered?: boolean
}

export interface Kpis {
  rides: number
  events: number
  alerts: number
  crashes: number
  dispatches: number
  takebacks: number
  avgFatigue: number
  maxFatigue: number
}

export interface RideBucket {
  day: string
  rides: number
}

export const LEVEL_COLOR: Record<Level, string> = {
  awake: 'var(--chart-1)',
  notice: 'var(--chart-2)',
  warn: 'var(--chart-4)',
  alarm: 'var(--chart-3)',
}
export const LEVEL_LABEL: Record<Level, string> = {
  awake: 'Awake',
  notice: 'Notice',
  warn: 'Warn',
  alarm: 'Alarm',
}

/* ── integration: runtime mode, live connection, alerts ─────────────── */

// live  = full /ws/fleet stream (telemetry tile updates continuously)
// alerts= same socket, tile updates ONLY on alerts (drowsy→alarm, crash, dispatch)
// seeded= offline demo driven by the in-browser simulator (no backend)
export type Mode = 'live' | 'alerts' | 'seeded'
export type ConnStatus = 'connecting' | 'online' | 'offline'

export interface DispatchRecord {
  incident_id: string
  driver_id: string
  severity: Severity
  location: { lat: number; lon: number; speed_mps?: number }
  dispatched_at: number
}

export interface VerifyResult {
  ok: boolean
  count: number
  broken_at: number | null
  checked_at: number
  reason?: string
}

export type AlertKind = 'drowsy' | 'crash' | 'dispatch'
export interface AlertItem {
  id: string
  ts: number
  kind: AlertKind
  title: string
  detail: string
  tone: 'warn' | 'alert' | 'ok'
}
