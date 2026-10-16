// Graph X-ray: remember the trace ids of the API calls made on the current page. Each id resolves
// to the named Cypher queries that request ran (GET /api/xray/{id}).

interface TraceRef {
  id: string
  path: string
  at: number
}

let page = ''
let traces: TraceRef[] = []
const listeners = new Set<() => void>()

/** Called on every route change: the X-ray shows only the current page's requests. */
export function startPage(path: string): void {
  if (path === page) return
  page = path
  traces = []
  listeners.forEach((l) => l())
}

export function addTrace(id: string, path: string): void {
  traces = [...traces.slice(-40), { id, path, at: Date.now() }]
  listeners.forEach((l) => l())
}

export function currentTraces(): TraceRef[] {
  return traces
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
