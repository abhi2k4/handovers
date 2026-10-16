import { useState } from 'react'

export interface Paged<T> {
  items: T[]
  page: number
  pages: number
  total: number
  from: number
  to: number
  setPage: (page: number) => void
}

/**
 * Client-side pagination for lists that can grow (people, sources, handovers). Pages, not infinite
 * scroll. The page goes back to 1 whenever `resetKey` changes (a new filter or search).
 */
export function usePaged<T>(rows: T[], size = 10, resetKey = ''): Paged<T> {
  const [state, setState] = useState({ key: resetKey, page: 0 })
  const pages = Math.max(1, Math.ceil(rows.length / size))
  const page = state.key === resetKey ? Math.min(state.page, pages - 1) : 0
  const start = page * size
  return {
    items: rows.slice(start, start + size),
    page,
    pages,
    total: rows.length,
    from: rows.length ? start + 1 : 0,
    to: Math.min(start + size, rows.length),
    setPage: (p) => setState({ key: resetKey, page: Math.max(0, Math.min(p, pages - 1)) }),
  }
}
