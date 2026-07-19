// Web-Audio alert chimes for the dashboard. Browsers block autoplay until a user
// gesture, so the context is created lazily and resumed on the first interaction
// (and whenever sound is toggled on). A persisted mute lets the operator silence it.

type Chime = 'notice' | 'warn' | 'alarm' | 'crash' | 'dispatch' | 'cancel'

let ctx: AudioContext | null = null

const MUTE_KEY = 'ridewme.muted'
function readMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === '1'
  } catch {
    return false
  }
}
let muted = readMuted()
const muteListeners = new Set<(m: boolean) => void>()

export function isMuted(): boolean {
  return muted
}
export function subscribeMute(cb: (m: boolean) => void): () => void {
  muteListeners.add(cb)
  return () => {
    muteListeners.delete(cb)
  }
}
export function setMuted(m: boolean): void {
  muted = m
  try {
    localStorage.setItem(MUTE_KEY, m ? '1' : '0')
  } catch {
    /* ignore */
  }
  muteListeners.forEach((l) => l(m))
  if (!m) arm() // unmuting is itself a gesture — arm the context
}
export function toggleMuted(): void {
  setMuted(!muted)
}

function ensureCtx(): AudioContext | null {
  if (ctx) return ctx
  try {
    const AC = window.AudioContext || (window as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (AC) ctx = new AC()
  } catch {
    ctx = null
  }
  return ctx
}

export function arm(): void {
  const c = ensureCtx()
  if (c && c.state === 'suspended') c.resume().catch(() => {})
}

// resume on the first user gesture anywhere on the page
if (typeof window !== 'undefined') {
  const onGesture = () => {
    arm()
    window.removeEventListener('pointerdown', onGesture)
    window.removeEventListener('keydown', onGesture)
  }
  window.addEventListener('pointerdown', onGesture)
  window.addEventListener('keydown', onGesture)
}

function tone(freq: number, dur: number, vol: number, delay = 0): void {
  const c = ctx
  if (!c) return
  const t0 = c.currentTime + delay
  const o = c.createOscillator()
  const g = c.createGain()
  o.type = 'sine'
  o.frequency.value = freq
  g.gain.setValueAtTime(0.0001, t0)
  g.gain.exponentialRampToValueAtTime(vol, t0 + 0.012)
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  o.connect(g)
  g.connect(c.destination)
  o.start(t0)
  o.stop(t0 + dur + 0.03)
}

// Distinct, proportionate patterns per alert. Mirrors the in-cabin/viz escalation.
export function chime(kind: Chime): void {
  if (muted) return
  const c = ensureCtx()
  if (!c) return
  if (c.state === 'suspended') c.resume().catch(() => {})
  switch (kind) {
    case 'notice':
      tone(440, 0.18, 0.06)
      break
    case 'warn':
      tone(600, 0.22, 0.11)
      tone(700, 0.22, 0.11, 0.22)
      break
    case 'alarm': // drowsiness alarm — urgent, repeating
      tone(900, 0.3, 0.16)
      tone(900, 0.3, 0.16, 0.4)
      tone(900, 0.3, 0.16, 0.8)
      break
    case 'crash': // crash confirmed — low, heavy
      tone(320, 0.5, 0.18)
      tone(240, 0.5, 0.18, 0.26)
      break
    case 'dispatch': // emergency dispatched — rising siren
      tone(880, 0.18, 0.18)
      tone(1100, 0.18, 0.18, 0.2)
      tone(1320, 0.34, 0.18, 0.4)
      break
    case 'cancel': // resolved — falling, reassuring
      tone(520, 0.18, 0.09)
      tone(400, 0.24, 0.09, 0.18)
      break
  }
}
