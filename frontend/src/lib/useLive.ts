import { useEffect, useState } from 'react'
import { liveSource } from './fleet'
import type { DriverState } from './types'

// Live driver state from the active source (edge WS in live/alerts, in-browser
// sim in seeded). Re-subscribes automatically when the mode changes.
export function useLive(): DriverState {
  const [state, setState] = useState<DriverState>(liveSource.value)
  useEffect(() => liveSource.subscribe(setState), [])
  return state
}
