// Backend wiring + dashboard runtime mode.
//
// The backend base URL is derived from wherever the page is served (so opening
// the dashboard at shawarma:5177 reaches the collector at shawarma:8080 across
// the tailnet). Override with VITE_BACKEND_URL. CORS on the backend is open.

import type { Mode } from './types'

const ENV = import.meta.env as unknown as Record<string, string | undefined>

function backendBase(): string {
  const explicit = ENV.VITE_BACKEND_URL?.trim()
  if (explicit) return explicit.replace(/\/+$/, '')
  if (typeof window !== 'undefined' && window.location.hostname) {
    const proto = window.location.protocol === 'https:' ? 'https' : 'http'
    return `${proto}://${window.location.hostname}:8080`
  }
  return 'http://127.0.0.1:8080'
}

export const HTTP_BASE = backendBase()
export const WS_BASE = HTTP_BASE.replace(/^http/, 'ws')
export const FLEET_WS = `${WS_BASE}/ws/fleet`
export const PRIMARY_DRIVER = (ENV.VITE_DRIVER_ID?.trim() || 'driver-1')
export const PRIMARY_NAME = (ENV.VITE_DRIVER_NAME?.trim() || 'Driver 1')

// Hardcoded nearest responder for the demo (matches the backend dispatch record).
export const HOSPITAL = {
  name: 'Apollo Spectra Hospitals — Koramangala, Bengaluru',
  short: 'Apollo Spectra · Koramangala',
  address:
    '143, 1st Cross Rd, near Nagarjuna Hotel, KHB Colony, 5th Block, Koramangala, Bengaluru, Karnataka 560095',
  emergencyLine: '1066',
}

/* ── runtime mode store (persisted across reloads) ──────────────────── */

const MODE_KEY = 'ridewme.mode'
const VALID: Mode[] = ['live', 'alerts', 'seeded']

function readMode(): Mode {
  try {
    const m = localStorage.getItem(MODE_KEY) as Mode | null
    if (m && VALID.includes(m)) return m
  } catch {
    /* localStorage unavailable */
  }
  return 'live'
}

let _mode: Mode = readMode()
const listeners = new Set<(m: Mode) => void>()

export function getMode(): Mode {
  return _mode
}

export function setMode(m: Mode): void {
  if (m === _mode) return
  _mode = m
  try {
    localStorage.setItem(MODE_KEY, m)
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => l(m))
}

export function subscribeMode(cb: (m: Mode) => void): () => void {
  listeners.add(cb)
  return () => {
    listeners.delete(cb)
  }
}
