import { useEffect, useState } from 'react'
import { ApiError } from '../lib/api'
import { notifyError, subscribe, type Notice } from '../lib/notify'
import { AlertTriangle, CheckCircle2, X } from './icons'

const SHOW_MS = 6000

/**
 * Messages from notify(), bottom right. Also the safety net for actions that forgot to catch:
 * an API call that fails without a handler shows the server's reason instead of doing nothing.
 */
export function Toaster() {
  const [notices, setNotices] = useState<Notice[]>([])

  useEffect(() => {
    const timers = new Set<number>()
    const off = subscribe((n) => {
      // The same message twice in a row (a double click) shows once.
      setNotices((all) => (all.some((a) => a.text === n.text) ? all : [...all.slice(-2), n]))
      const t = window.setTimeout(() => {
        setNotices((all) => all.filter((a) => a.id !== n.id))
        timers.delete(t)
      }, SHOW_MS)
      timers.add(t)
    })
    const onUnhandled = (e: PromiseRejectionEvent) => {
      if (e.reason instanceof ApiError) {
        e.preventDefault()
        notifyError(e.reason)
      }
    }
    window.addEventListener('unhandledrejection', onUnhandled)
    return () => {
      off()
      timers.forEach((t) => window.clearTimeout(t))
      window.removeEventListener('unhandledrejection', onUnhandled)
    }
  }, [])

  return (
    <div aria-live="polite" role="status" className="pointer-events-none fixed right-4 bottom-4 left-4 z-[60] flex flex-col items-end gap-2 sm:left-auto">
      {notices.map((n) => (
        <div
          key={n.id}
          className="pointer-events-auto flex w-full max-w-[400px] items-start gap-2.5 rounded-[6px] bg-page px-3.5 py-3 text-[14px] text-ink shadow-[0_12px_32px_rgba(15,27,45,0.18),0_0_0_1px_var(--color-line)]"
        >
          {n.tone === 'error' ? (
            <AlertTriangle size={18} className="mt-px shrink-0 text-risk-text" aria-hidden />
          ) : (
            <CheckCircle2 size={18} className="mt-px shrink-0 text-ok-text" aria-hidden />
          )}
          <span className="min-w-0 flex-1">{n.text}</span>
          <button
            onClick={() => setNotices((all) => all.filter((a) => a.id !== n.id))}
            aria-label="Dismiss"
            className="-m-1 flex size-6 shrink-0 items-center justify-center rounded-[4px] text-ink-3 hover:bg-hover hover:text-ink"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
