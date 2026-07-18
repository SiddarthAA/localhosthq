/** Minimal client-side auth (demo). One standard account. */
const KEY = 'ridewme.auth'
const VALID = { email: 'admin@ridewme.in', password: 'password' }

export type Session = { email: string; ts: number }

export function login(email: string, password: string): boolean {
  const ok =
    email.trim().toLowerCase() === VALID.email && password === VALID.password
  if (ok) {
    const session: Session = { email: VALID.email, ts: Date.now() }
    localStorage.setItem(KEY, JSON.stringify(session))
  }
  return ok
}

export function logout() {
  localStorage.removeItem(KEY)
}

export function isAuthed(): boolean {
  return Boolean(localStorage.getItem(KEY))
}

export function currentUser(): Session | null {
  const raw = localStorage.getItem(KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as Session
  } catch {
    return null
  }
}
