import { Check, ChevronRight } from './icons'
import { useState } from 'react'
import { Link } from 'react-router'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { ago } from '../lib/format'
import { Bar, Card, CardHeader, Chip } from './ui'

interface ReadinessItem {
  key: string
  label: string
  done: boolean
  detail: string
  owner: string
  action: string | null
  href: string
  /** The viewer can act on it; others see who it is waiting on. */
  mine: boolean
  /** The viewer can nudge whoever it waits on (HR, the manager). */
  remind: boolean
  reminded_at: number | null
}

/** Nudge the owner of a step (in the app, and on WhatsApp when they opted in). */
function Remind({ hid, item, now, onDone }: { hid: string; item: ReadinessItem; now: number; onDone: () => void }) {
  const [state, setState] = useState<'idle' | 'busy' | 'error'>('idle')
  const [error, setError] = useState('')
  async function send() {
    setState('busy')
    try {
      await api.post(`/handovers/${encodeURIComponent(hid)}/remind`, { step: item.key })
      setState('idle')
      onDone()
    } catch (e) {
      setState('error')
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }
  return (
    <span className="flex items-center gap-3 text-[13px]">
      <span className="text-ink-3">
        {state === 'error' ? error : item.reminded_at ? `Reminded ${ago(item.reminded_at, now)}` : `Waiting on ${item.owner}`}
      </span>
      <button onClick={send} disabled={state === 'busy'} className="font-medium text-accent hover:underline disabled:opacity-50">
        {state === 'busy' ? 'Sending…' : 'Remind'}
      </button>
    </span>
  )
}

interface Readiness {
  handover: string
  days_left: number
  done: number
  total: number
  ready: boolean
  items: ReadinessItem[]
  now: number
}

/**
 * "Ready by the last day?": every check that blocks a clean handover, who owns it and where to fix it.
 * Built server-side from the graph (GET /handovers/{id}/readiness).
 */
export function ReadinessCard({ hid }: { hid: string }) {
  const { data: r, reload } = useApi<Readiness>(`/handovers/${encodeURIComponent(hid)}/readiness`)
  if (!r) return null
  const late = !r.ready && r.days_left < 7

  return (
    <Card>
      <CardHeader
        title="Ready by the last day?"
        meta={`${r.done}/${r.total}`}
        right={
          r.ready ? (
            <Chip tone="ok">Ready</Chip>
          ) : (
            <Chip tone={late ? 'risk' : 'soon'}>{r.days_left === 1 ? '1 day left' : `${r.days_left} days left`}</Chip>
          )
        }
      />
      <div className="mb-3">
        <Bar value={r.done} max={r.total} risk={late} />
      </div>
      <ul className="-mx-2 flex flex-col">
        {r.items.map((i) => {
          const body = (
            <>
              <span
                className={`flex size-4 items-center justify-center rounded-[3px] ${
                  i.done ? 'bg-ok text-white' : 'shadow-[inset_0_0_0_1.25px_var(--color-strong)]'
                }`}
              >
                {i.done && <Check size={10} weight="bold" />}
              </span>
              <span className="min-w-0">
                <span className={`block truncate text-[14px] ${i.done ? 'text-ink-3' : 'font-medium'}`}>{i.label}</span>
                <span className="block truncate text-[13px] text-ink-3">
                  {i.detail} · {i.owner}
                </span>
              </span>
              {i.mine && i.action ? (
                <span className="flex items-center gap-0.5 text-[13px] font-medium text-accent">
                  {i.action}
                  <ChevronRight size={14} strokeWidth={1.75} />
                </span>
              ) : i.remind ? (
                <Remind hid={hid} item={i} now={r.now} onDone={reload} />
              ) : !i.done ? (
                <span className="text-[13px] text-ink-3">Waiting on {i.owner}</span>
              ) : (
                <span />
              )}
            </>
          )
          const row = 'grid grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-3 rounded-[4px] px-2 py-2'
          return (
            <li key={i.key}>
              {i.mine ? (
                <Link to={i.href} className={`${row} transition-colors duration-150 hover:bg-app`}>
                  {body}
                </Link>
              ) : (
                <div className={row}>{body}</div>
              )}
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
