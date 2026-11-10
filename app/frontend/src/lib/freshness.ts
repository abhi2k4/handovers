import { useSyncExternalStore } from 'react'

// When shared data (sidebar counts, who "me" is and what they take part in) may have changed:
// after any successful change made through the API (lib/api.ts), and when the person comes back
// to the tab (background jobs may have sent alerts). Reading it in a request key refetches then,
// instead of on every page change.

let version = 0
const listeners = new Set<() => void>()

export function dataChanged(): void {
  version += 1
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  if (listeners.size === 1) document.addEventListener('visibilitychange', onVisible)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) document.removeEventListener('visibilitychange', onVisible)
  }
}

function onVisible(): void {
  if (document.visibilityState === 'visible') dataChanged()
}

export function useDataVersion(): number {
  return useSyncExternalStore(subscribe, () => version)
}
