import { useState } from 'react'

export const TOUR_SEEN = 'handovers.tourSeen'

function seen(): boolean {
  try {
    return localStorage.getItem(TOUR_SEEN) === '1'
  } catch {
    return true
  }
}

/** The guide opens automatically on the first visit; `show()` reopens it. */
export function useTour() {
  const [open, setOpen] = useState(() => !seen())
  return { open, show: () => setOpen(true), hide: () => setOpen(false) }
}
