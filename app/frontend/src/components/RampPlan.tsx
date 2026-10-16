import { Check, MessageSquareText, X } from './icons'
import { useState } from 'react'
import { Link } from 'react-router'
import { useApi } from '../hooks/useApi'
import { useViewAs } from '../hooks/useViewAs'
import { api } from '../lib/api'
import { Bar, Button, Card, CardHeader, Chip } from './ui'

interface RampItem {
  id: string
  week: number
  kind: string
  title: string
  why: string
  about: string | null
  done_at: number | null
}

interface Plan {
  status: 'none' | 'draft' | 'approved'
  method?: string
  approved_by?: string | null
  items: RampItem[]
  done: number
  total: number
}

const WEEKS: Record<number, string> = { 1: 'Week 1', 2: 'Week 2', 3: 'Weeks 3–4' }

/** The question a successor would otherwise ask the person who left; null where memory cannot help. */
function askHow(i: Pick<RampItem, 'kind' | 'title'>): string | null {
  const subject = i.title.includes(': ') ? i.title.slice(i.title.indexOf(': ') + 2) : i.title
  const lower = /^[A-Z][a-z]/.test(subject) ? subject[0].toLowerCase() + subject.slice(1) : subject
  switch (i.kind) {
    case 'take-over':
    case 'shadow':
    case 'own':
    case 'practise':
      return `How do I ${lower}?`
    case 'read':
      return `Why did we decide: ${subject}?`
    case 'coordinate':
      return `Who else works on ${lower}, and how is it split?`
    default:
      return null
  }
}

/**
 * Successor ramp-up plan (product-strategy section 11): built from the leaver's work in the graph.
 * `manager` mode creates, edits and approves the draft; `successor` mode ticks items off.
 */
export function RampPlan({
  hid,
  mode,
  successor,
  canApprove = true,
}: {
  hid: string
  mode: 'manager' | 'successor'
  successor: string
  /** False for HR: sees and creates the plan, but only the manager edits and approves it. */
  canApprove?: boolean
}) {
  const { me } = useViewAs()
  const { data: plan, error, reload } = useApi<Plan>(`/handovers/${encodeURIComponent(hid)}/ramp`)
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  async function act(fn: () => Promise<unknown>) {
    setBusy(true)
    setFailure(null)
    try {
      await fn()
      reload()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const title = mode === 'manager' ? `Ramp-up plan for ${successor}` : 'Your first 30 days'
  if (error) return null
  if (!plan) return null

  if (plan.status !== 'approved' && mode === 'successor') {
    return (
      <Card>
        <CardHeader title={title} />
        <p className="text-ink-2">Your manager is preparing it from your predecessor&apos;s work. It appears here once approved.</p>
      </Card>
    )
  }

  if (plan.status === 'none') {
    return (
      <Card>
        <CardHeader title={title} />
        <p className="mb-4 text-ink-2">
          A first-month plan from the leaver&apos;s work: access, recurring work, people and decisions. You review it before {successor} sees it.
        </p>
        <Button disabled={busy} onClick={() => void act(() => api.post(`/handovers/${encodeURIComponent(hid)}/ramp`))}>
          {busy ? 'Creating…' : 'Create ramp-up plan'}
        </Button>
        {failure && <p className="mt-2 text-[13px] text-risk-text">{failure}</p>}
      </Card>
    )
  }

  const draft = plan.status === 'draft'
  const pct = plan.total ? Math.round((100 * plan.done) / plan.total) : 0
  const weeks = [1, 2, 3].filter((w) => plan.items.some((i) => i.week === w))

  return (
    <Card>
      <CardHeader
        title={title}
        meta={draft ? 'Draft' : `${plan.done}/${plan.total}`}
        right={
          draft ? (
            mode === 'manager' && canApprove && (
              <Button disabled={busy} onClick={() => void act(() => api.post(`/handovers/${encodeURIComponent(hid)}/ramp/approve`))}>
                Approve plan
              </Button>
            )
          ) : (
            <Chip tone="ok">Approved</Chip>
          )
        }
      />
      {!draft && (
        <div className="mb-4">
          <Bar value={pct} max={100} />
          <div className="mt-1 text-[13px] text-ink-3">{pct}% done</div>
        </div>
      )}
      {draft && mode === 'manager' && (
        <p className="mb-4 text-[13px] text-ink-3">
          {canApprove ? `Move or remove items, then approve. ${successor} sees it after approval.` : `Waiting for the manager to approve. ${successor} sees it after approval.`}
        </p>
      )}
      <div className="flex flex-col gap-5">
        {weeks.map((w) => (
          <section key={w}>
            <h3 className="mb-2 text-[13px] font-medium text-ink-3">{WEEKS[w]}</h3>
            <ul className="flex flex-col divide-y divide-line">
              {plan.items
                .filter((i) => i.week === w)
                .map((i) => (
                  <li key={i.id} className="flex items-start gap-3 py-2.5">
                    {mode === 'successor' && !draft ? (
                      <button
                        aria-label={i.done_at ? 'Mark as not done' : 'Mark as done'}
                        disabled={busy}
                        onClick={() => void act(() => api.post(`/ramp-items/${encodeURIComponent(i.id)}`, { done: !i.done_at }))}
                        className={`mt-0.5 flex size-[18px] shrink-0 items-center justify-center rounded-[4px] transition-colors ${
                          i.done_at ? 'bg-ok text-white' : 'shadow-[inset_0_0_0_1.5px_var(--color-control)] hover:bg-hover'
                        }`}
                      >
                        {i.done_at && <Check size={12} strokeWidth={3} />}
                      </button>
                    ) : (
                      <span className={`mt-[7px] size-1.5 shrink-0 rounded-full ${i.done_at ? 'bg-ok' : 'bg-accent-fill'}`} />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className={`text-[14px] ${i.done_at ? 'text-ink-3 line-through' : 'text-ink'}`}>{i.title}</div>
                      <div className="text-[13px] text-ink-3">{i.why}</div>
                    </div>
                    {mode === 'successor' && !draft && !i.done_at && askHow(i) && (
                      <Link
                        to={`/ask?as=${encodeURIComponent(me?.id ?? '')}&q=${encodeURIComponent(askHow(i) ?? '')}`}
                        className="flex shrink-0 items-center gap-1 rounded-[4px] px-1.5 py-1 text-[13px] text-accent hover:bg-hover"
                      >
                        <MessageSquareText size={13} strokeWidth={1.9} />
                        Ask how
                      </Link>
                    )}
                    {draft && mode === 'manager' && canApprove && (
                      <div className="flex shrink-0 items-center gap-1">
                        <select
                          aria-label="Move to week"
                          value={i.week}
                          disabled={busy}
                          onChange={(e) => void act(() => api.post(`/ramp-items/${encodeURIComponent(i.id)}`, { week: Number(e.target.value) }))}
                          className="h-7 rounded-[4px] bg-page px-1.5 text-[13px] shadow-[inset_0_0_0_1px_var(--color-control)]"
                        >
                          {[1, 2, 3].map((n) => (
                            <option key={n} value={n}>
                              {WEEKS[n]}
                            </option>
                          ))}
                        </select>
                        <button
                          aria-label="Remove item"
                          disabled={busy}
                          onClick={() => void act(() => api.post(`/ramp-items/${encodeURIComponent(i.id)}`, { removed: true }))}
                          className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-risk-text"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </li>
                ))}
            </ul>
          </section>
        ))}
      </div>
      {failure && <p className="mt-3 text-[13px] text-risk-text">{failure}</p>}
    </Card>
  )
}
