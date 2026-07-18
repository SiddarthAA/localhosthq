// Live edge feed: one WebSocket to the collector's /ws/fleet, reduced into the
// dashboard's DriverState + an alerts stream. Auto-reconnects.
//
// The backend's `state` deltas carry score/level/duty/incident but NOT the
// per-signal detail — that arrives on `event` (drowsiness) messages — so this
// merges both into one DriverState. Backend ts are seconds → ×1000 for the UI.

import { toast } from 'sonner'
import { FLEET_WS, PRIMARY_DRIVER, PRIMARY_NAME, getMode, subscribeMode } from './config'
import { mapIncident } from './api'
import { liveSim } from './data'
import type { AlertItem, ConnStatus, DriverState, Level, Severity, SignalKey } from './types'

const SEC = 1000
type Listener = (s: DriverState) => void

function defaultState(): DriverState {
  return {
    driver_id: PRIMARY_DRIVER,
    name: PRIMARY_NAME,
    online: false,
    session_id: '',
    level: 'awake',
    score: 0,
    gated: false,
    signals: { ear: 0, perclos: 0, blink_rate: 0, blink_dur_ms: 0, head_nod: 0, yawn: 0 },
    fired: [],
    agree_count: 0,
    duty: 'idle',
    fps: 0,
    speed_mps: 0,
    calibrated: false,
    link: 'offline',
    pending: 0,
    last_event_ts: 0,
    updated_at: 0,
    active_incident: null,
  }
}

// backend drowsiness "fired" names → the dashboard's SignalKey bars
function mapFired(fired: string[]): SignalKey[] {
  const out = new Set<SignalKey>()
  for (const f of fired ?? []) {
    if (f === 'eyes') {
      out.add('perclos')
      out.add('blink')
    } else if (f === 'head_nod' || f === 'yawn' || f === 'perclos' || f === 'blink') {
      out.add(f)
    }
  }
  return [...out]
}

/* ── connection-status store ────────────────────────────────────────── */
let _conn: ConnStatus = 'offline'
const connListeners = new Set<(c: ConnStatus) => void>()
function setConn(c: ConnStatus) {
  if (c === _conn) return
  _conn = c
  connListeners.forEach((l) => l(c))
}
export function getConn(): ConnStatus {
  return _conn
}
export function subscribeConn(cb: (c: ConnStatus) => void): () => void {
  connListeners.add(cb)
  return () => {
    connListeners.delete(cb)
  }
}

/* ── alerts stream ──────────────────────────────────────────────────── */
const _alerts: AlertItem[] = []
const alertListeners = new Set<(a: AlertItem[]) => void>()
let _aid = 0
function pushAlert(a: Omit<AlertItem, 'id'>) {
  _alerts.unshift({ ...a, id: `a${++_aid}` })
  if (_alerts.length > 40) _alerts.length = 40
  const snap = [..._alerts]
  alertListeners.forEach((l) => l(snap))
}
export function getAlerts(): AlertItem[] {
  return _alerts
}
export function subscribeAlerts(cb: (a: AlertItem[]) => void): () => void {
  alertListeners.add(cb)
  return () => {
    alertListeners.delete(cb)
  }
}

/* ── the fleet websocket client ─────────────────────────────────────── */
class FleetClient {
  private state = defaultState()
  private listeners = new Set<Listener>()
  private started = false
  private retry = 0
  private timer: ReturnType<typeof setTimeout> | null = null

  get value(): DriverState {
    return this.state
  }

  subscribe(cb: Listener): () => void {
    this.listeners.add(cb)
    cb(this.state)
    return () => {
      this.listeners.delete(cb)
    }
  }

  ensureConnected() {
    if (this.started) return
    this.started = true
    this.connect()
  }

  private connect() {
    setConn('connecting')
    let ws: WebSocket
    try {
      ws = new WebSocket(FLEET_WS)
    } catch {
      this.scheduleReconnect()
      return
    }
    ws.onopen = () => {
      this.retry = 0
      setConn('online')
    }
    ws.onmessage = (ev) => this.onMessage(ev.data as string)
    ws.onclose = () => {
      setConn('offline')
      this.markOffline()
      this.scheduleReconnect()
    }
    ws.onerror = () => {
      try {
        ws.close()
      } catch {
        /* noop */
      }
    }
  }

  private scheduleReconnect() {
    if (this.timer) return
    const delay = Math.min(8000, 800 * 2 ** Math.min(this.retry, 4))
    this.retry++
    this.timer = setTimeout(() => {
      this.timer = null
      this.connect()
    }, delay)
  }

  private markOffline() {
    this.state = { ...this.state, online: false, link: 'offline' }
    this.listeners.forEach((l) => l(this.state))
  }

  private emit(isAlert: boolean) {
    // alerts-only mode: the tile updates only when an alert fires
    if (getMode() === 'alerts' && !isAlert) return
    this.listeners.forEach((l) => l(this.state))
  }

  private onMessage(raw: string) {
    let msg: any
    try {
      msg = JSON.parse(raw)
    } catch {
      return
    }
    switch (msg.kind) {
      case 'snapshot': {
        const d = (msg.drivers ?? []).find((x: any) => x.driver_id === PRIMARY_DRIVER)
        if (d) this.applyState(d)
        this.emit(false)
        return
      }
      case 'state': {
        if (msg.driver?.driver_id !== PRIMARY_DRIVER) return
        this.applyState(msg.driver)
        this.emit(false)
        return
      }
      case 'event': {
        const e = msg.event
        if (!e || e.driver_id !== PRIMARY_DRIVER) return
        this.applyEvent(e)
        return
      }
      case 'dispatch': {
        if (msg.driver_id !== PRIMARY_DRIVER) return
        const inc = msg.incident ?? {}
        const loc = inc.location ?? {}
        pushAlert({
          ts: Date.now(),
          kind: 'dispatch',
          tone: 'alert',
          title: 'Emergency dispatched',
          detail: `${inc.severity ?? 'crash'} · responder @ ${(loc.lat ?? 0).toFixed(3)}, ${(loc.lon ?? 0).toFixed(3)}`,
        })
        toast.error('Emergency dispatched', {
          description: `${inc.severity ?? 'crash'} confirmed — responder notified`,
        })
        this.emit(true)
        return
      }
      default:
        return
    }
  }

  private applyState(d: Record<string, any>) {
    this.state = {
      ...this.state,
      session_id: d.session_id ?? this.state.session_id,
      level: (d.level ?? this.state.level) as Level,
      score: typeof d.score === 'number' ? d.score : this.state.score,
      gated: !!d.gated,
      duty: d.duty ?? this.state.duty,
      fps: typeof d.fps === 'number' ? d.fps : this.state.fps,
      speed_mps: typeof d.speed_mps === 'number' ? d.speed_mps : 0,
      calibrated: !!d.calibrated,
      link: d.link ?? this.state.link,
      pending: d.pending ?? 0,
      online: d.online ?? true,
      active_incident: d.active_incident ? mapIncident(d.active_incident) : null,
      last_event_ts: (d.last_event_ts ?? 0) * SEC,
      updated_at: (d.updated_at ?? 0) * SEC || Date.now(),
    }
  }

  private applyEvent(e: Record<string, any>) {
    const p = e.payload ?? {}
    if (e.type === 'drowsiness') {
      const prevLevel = this.state.level
      const level = (p.level ?? this.state.level) as Level
      const s = p.signals ?? {}
      this.state = {
        ...this.state,
        score: typeof p.score === 'number' ? p.score : this.state.score,
        level,
        gated: !!p.gated,
        calibrated: p.calibrated ?? this.state.calibrated,
        signals: {
          ear: s.ear ?? 0,
          perclos: s.perclos ?? 0,
          blink_rate: s.blink_rate ?? 0,
          blink_dur_ms: s.blink_dur_ms ?? 0,
          head_nod: s.head_nod ?? 0,
          yawn: s.yawn ?? 0,
        },
        fired: mapFired(p.fired ?? []),
        agree_count: p.agree_count ?? 0,
        online: true,
        updated_at: Date.now(),
        last_event_ts: (e.ts ?? 0) * SEC,
      }
      const isAlarm = p.kind === 'transition' && level === 'alarm' && prevLevel !== 'alarm'
      if (isAlarm) {
        pushAlert({
          ts: Date.now(),
          kind: 'drowsy',
          tone: 'alert',
          title: 'Drowsiness alarm',
          detail: `${this.state.name} · score ${Math.round(p.score ?? 0)} · ${((p.fired ?? []) as string[]).join(', ') || 'eyes'}`,
        })
        toast.warning('Drowsiness alarm', {
          description: `${this.state.name} — sustained eye closure`,
        })
      }
      this.emit(isAlarm)
      return
    }
    if (e.type === 'crash') {
      const card = mapIncident(p)
      this.state = { ...this.state, active_incident: card, online: true, updated_at: Date.now() }
      if (card.status === 'unconfirmed') {
        pushAlert({
          ts: Date.now(),
          kind: 'crash',
          tone: 'warn',
          title: 'Possible crash',
          detail: `${card.severity} · peak ${card.peak_g.toFixed(1)}g · fleet-only, ${card.cancel_window_s}s cancel window`,
        })
        toast('Possible crash detected', { description: `${card.severity} — awaiting confirmation` })
      } else if (card.status === 'confirmed') {
        pushAlert({
          ts: Date.now(),
          kind: 'crash',
          tone: 'alert',
          title: 'Crash confirmed',
          detail: `${card.severity} · vehicle ${card.final_motion ?? 'stopped'}`,
        })
        toast.error('Crash confirmed', { description: `${card.severity} — dispatching responder` })
      } else if (card.status === 'cancelled') {
        pushAlert({
          ts: Date.now(),
          kind: 'crash',
          tone: 'ok',
          title: 'Crash cancelled',
          detail: card.reason === 'driver' ? 'Driver cancelled' : 'De-escalated (vehicle moving)',
        })
        toast.success('Crash cancelled', {
          description: card.reason === 'driver' ? "Driver is OK" : 'De-escalated',
        })
      }
      this.emit(true)
      return
    }
    if (e.type === 'heartbeat') {
      this.state = {
        ...this.state,
        fps: typeof p.fps === 'number' ? p.fps : this.state.fps,
        duty: p.duty ?? this.state.duty,
        link: p.link ?? this.state.link,
        pending: p.pending ?? this.state.pending,
        speed_mps: typeof p.speed_mps === 'number' ? p.speed_mps : this.state.speed_mps,
        calibrated: p.calibrated ?? this.state.calibrated,
        online: true,
        updated_at: Date.now(),
        last_event_ts: (e.ts ?? 0) * SEC,
      }
      this.emit(false)
      return
    }
    // hello / anything else → not shown on the tile
  }
}

const fleet = new FleetClient()

/* ── unified source: live/alerts = fleet WS, seeded = in-browser sim ─── */
export const liveSource = {
  get value(): DriverState {
    return getMode() === 'seeded' ? liveSim.value : fleet.value
  },
  subscribe(cb: Listener): () => void {
    let inner: (() => void) | null = null
    const attach = () => {
      inner?.()
      if (getMode() === 'seeded') {
        inner = liveSim.subscribe(cb)
      } else {
        fleet.ensureConnected()
        inner = fleet.subscribe(cb)
      }
    }
    attach()
    const offMode = subscribeMode(attach)
    return () => {
      inner?.()
      offMode()
    }
  },
  pushDrowsy() {
    if (getMode() === 'seeded') liveSim.pushDrowsy()
  },
  triggerCrash(severity: Severity = 'severe') {
    if (getMode() === 'seeded') liveSim.triggerCrash(severity)
  },
  setNaive(on: boolean) {
    if (getMode() === 'seeded') liveSim.setNaive(on)
  },
  cancelCrash() {
    if (getMode() === 'seeded') liveSim.cancelCrash()
  },
}
