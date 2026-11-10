// Short messages after an action ("Saved", or why it failed), shown by <Toaster/> in the app
// layout. Any screen can call notify() without passing callbacks around.

export interface Notice {
  id: number
  text: string
  tone: 'ok' | 'error'
}

type Listener = (notice: Notice) => void

const listeners = new Set<Listener>()
let next = 0

export function notify(text: string, tone: Notice['tone'] = 'ok'): void {
  const notice = { id: ++next, text, tone }
  listeners.forEach((l) => l(notice))
}

/** Say why an action failed, using the server's own message when there is one. */
export function notifyError(error: unknown, fallback = 'That did not work. Try again.'): void {
  notify(error instanceof Error && error.message ? error.message : fallback, 'error')
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
