import { addTrace } from './trace'
import { getViewAs } from './viewAs'

// Single place for HTTP calls. Every request is same-origin `/api/*`:
// Vite proxies it to FastAPI in dev; nginx does the same in Docker.

export class ApiError extends Error {
  readonly status: number
  /** Set when the server asks the user to confirm first (e.g. a successor from another team). */
  readonly confirm: { code: string; message: string } | null

  constructor(status: number, message: string, confirm: { code: string; message: string } | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.confirm = confirm
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(getViewAs() ? { 'X-View-As': getViewAs() } : {}),
      ...init?.headers,
    },
  })
  const traceId = response.headers.get('X-Trace-Id')
  if (traceId) addTrace(traceId, path)
  if (!response.ok) {
    let message = `Something went wrong (${response.status}).`
    let confirm: { code: string; message: string } | null = null
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') message = body.detail
      else if (body.detail && typeof body.detail === 'object') {
        const d = body.detail as { code?: string; message?: string; confirm?: boolean }
        if (d.message) message = d.message
        if (d.confirm && d.code) confirm = { code: d.code, message }
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(response.status, message, confirm)
  }
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  form: <T>(path: string, data: FormData) => request<T>(path, { method: 'POST', body: data }),
}
