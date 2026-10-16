import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'

interface Settled<T> {
  key: string | null
  data: T | null
  error: string | null
}

/** GET a path; re-fetches when the path changes. `reload()` fetches again. */
export function useApi<T>(path: string | null) {
  const [tick, setTick] = useState(0)
  const [settled, setSettled] = useState<Settled<T>>({ key: null, data: null, error: null })
  // Identifies the request we want; `loading` is derived instead of set inside the effect.
  const key = path ? `${tick}:${path}` : null

  useEffect(() => {
    if (!path || !key) return
    const controller = new AbortController()
    api
      .get<T>(path, controller.signal)
      .then((data) => setSettled({ key, data, error: null }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setSettled({ key, data: null, error: err instanceof Error ? err.message : 'Failed to load' })
      })
    return () => controller.abort()
  }, [path, key])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  const current = settled.key === key
  return {
    // Keep showing the last data while a new request is in flight (as before).
    data: settled.data,
    error: current ? settled.error : null,
    loading: key !== null && !current,
    reload,
  }
}
