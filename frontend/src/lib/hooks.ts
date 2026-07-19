import { useEffect, useState } from 'react'
import { getMode, setMode, subscribeMode } from './config'
import { getAlerts, getConn, subscribeAlerts, subscribeConn } from './fleet'
import { isMuted, subscribeMute, toggleMuted } from './sound'
import { getHistory } from './data'
import { buildHistory } from './api'
import type { History } from './data'
import type { AlertItem, ConnStatus, Mode } from './types'

export function useMode(): [Mode, (m: Mode) => void] {
  const [m, setM] = useState<Mode>(getMode)
  useEffect(() => subscribeMode(setM), [])
  return [m, setMode]
}

export function useConn(): ConnStatus {
  const [c, setC] = useState<ConnStatus>(getConn)
  useEffect(() => subscribeConn(setC), [])
  return c
}

export function useAlerts(): AlertItem[] {
  const [a, setA] = useState<AlertItem[]>(getAlerts)
  useEffect(() => subscribeAlerts(setA), [])
  return a
}

export function useMuted(): [boolean, () => void] {
  const [m, setM] = useState<boolean>(isMuted)
  useEffect(() => subscribeMute(setM), [])
  return [m, toggleMuted]
}

const EMPTY_HISTORY: History = {
  fatigue: [],
  duty: [],
  rides: [],
  incidents: [],
  ledger: [],
  kpis: { rides: 0, events: 0, alerts: 0, crashes: 0, dispatches: 0, takebacks: 0, avgFatigue: 0, maxFatigue: 0 },
  levelDist: [
    { level: 'awake', seconds: 0 },
    { level: 'notice', seconds: 0 },
    { level: 'warn', seconds: 0 },
    { level: 'alarm', seconds: 0 },
  ],
  signalFreq: [],
}

// One shared history store so all chart/KPI components trigger a SINGLE ledger
// fetch (not one per component), deduped by data key (live+alerts share the same
// REST-derived history; seeded uses the in-browser synth). Refreshes periodically
// in remote mode so the charts absorb events that stream in during a live demo.
const REFRESH_MS = 30_000
const store = {
  data: EMPTY_HISTORY,
  loadedKey: null as 'seeded' | 'remote' | null,
  inflight: false,
  timer: null as ReturnType<typeof setInterval> | null,
  listeners: new Set<(h: History) => void>(),
  emit() {
    const d = this.data
    this.listeners.forEach((l) => l(d))
  },
  subscribe(cb: (h: History) => void) {
    this.listeners.add(cb)
    return () => {
      this.listeners.delete(cb)
    }
  },
  load(mode: Mode) {
    const key = mode === 'seeded' ? 'seeded' : 'remote'
    if (key === 'seeded') {
      this.loadedKey = 'seeded'
      this.data = getHistory()
      this.emit()
      return
    }
    if (this.loadedKey === 'remote' || this.inflight) return
    this.inflight = true
    this.data = EMPTY_HISTORY
    this.emit()
    buildHistory()
      .then((h) => {
        this.data = h
        this.loadedKey = 'remote'
        this.inflight = false
        this.emit()
        this.startRefresh()
      })
      .catch(() => {
        this.inflight = false
      })
  },
  startRefresh() {
    if (this.timer) return
    this.timer = setInterval(() => {
      if (this.loadedKey !== 'remote') return
      buildHistory()
        .then((h) => {
          this.data = h
          this.emit()
        })
        .catch(() => {
          /* transient — keep last good history */
        })
    }, REFRESH_MS)
  },
}

// Mode-aware history shared across all consumers. Returns a usable History
// immediately (empty while the first fetch resolves) so the existing chart
// components keep destructuring it unchanged.
export function useHistory(): History {
  const [mode] = useMode()
  const [data, setData] = useState<History>(store.data)
  useEffect(() => {
    const off = store.subscribe(setData)
    setData(store.data)
    store.load(mode)
    return off
  }, [mode])
  return data
}
