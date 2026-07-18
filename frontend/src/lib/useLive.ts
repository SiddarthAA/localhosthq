import { useEffect, useState } from 'react'
import { liveSim } from './data'
import type { DriverState } from './types'

export function useLive(): DriverState {
  const [state, setState] = useState<DriverState>(liveSim.value)
  useEffect(() => liveSim.subscribe(setState), [])
  return state
}
