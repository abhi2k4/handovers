import { useState } from 'react'
import { Check, Lock, Printer } from '../../components/icons'
import { Bar, Button, Card, CardHeader, Chip, ErrorNote, Input, Loading, TextArea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { api } from '../../lib/api'
import { date, first } from '../../lib/format'
import type { Handover } from '../../types/api'

interface Row {
  key: string
  target: string
  label: string
  group: string
  owner: string
  status: 'open' | 'done' | 'confirmed'
  by: string | null
  auto: boolean
}

interface Letter {
  date: string
  to: string
  subject: string
  body: string[]
  signatory: { name: string; title: string }
}

interface Proposal {
  id: string
  account: string
  account_name: string
  to: string
  to_name: string
  proposed_by: string
  proposed_at: number
  note: string | null
}

interface Clearance {
  items: Row[]
  confirmed: number
  total: number
  complete: boolean
  can_confirm: boolean
  can_mark: boolean
  transferred: boolean
  letter: Letter | null
  letter_gate: { can_send: boolean; reason: string; ready_at: number | null }
  letter_sent_at: number | null
  letter_scheduled_at: number | null
  email_draft: { to: string; subject: string; body: string } | null
  proposals: Proposal[]
}

interface Actions {
  set: (key: string, status: Row['status']) => void
  /** Do the work in the graph: reassign the admin, or give the work to the successor. */
  hand: (r: Row) => void
  successor: string | null
  /** Work can only go to someone who has already joined. */
  successorActive: boolean
  /** Accounts with a handover proposed and waiting for HR. */
  proposed: Set<string>
}

function RowView({ r, c, a }: { r: Row; c: Clearance; a: Actions }) {
  const graphRow = r.key.startsWith('admin:') || (r.key.startsWith('work:') && a.successorActive)
  return (
    <li className="grid grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-3 py-2.5">
      <span
        className={`flex size-4 items-center justify-center rounded-[3px] ${
          r.status === 'confirmed' ? 'bg-ok text-white' : r.status === 'done' ? 'bg-ok-soft text-ok-text' : 'shadow-[inset_0_0_0_1.25px_var(--color-strong)]'
        }`}
      >
        {r.status !== 'open' && <Check size={10} weight="bold" />}
      </span>
      <span className="min-w-0">
        <span className={`block truncate text-[14px] ${r.status === 'confirmed' ? 'text-ink-3' : 'font-medium'}`}>{r.label}</span>
        <span className="block text-[13px] text-ink-3">
          {r.owner}
          {r.status === 'done' && ` · done${r.by ? ` by ${r.by}` : ''}, waiting for HR`}
          {r.status === 'confirmed' && (r.auto ? ` · now with ${r.by}` : ` · confirmed${r.by ? ` by ${r.by}` : ''}`)}
        </span>
      </span>
      <span className="flex items-center gap-3 text-[13px] font-medium">
        {r.status === 'open' && c.can_mark && graphRow && a.successor && !a.proposed.has(r.target) && (
          <button onClick={() => a.hand(r)} className="text-accent hover:underline">
            {r.key.startsWith('admin:') ? `Give admin to ${first(a.successor)}` : `Give to ${first(a.successor)}`}
          </button>
        )}
        {r.status === 'open' && c.can_mark && !(graphRow && a.successor) && (
          <button onClick={() => a.set(r.key, 'done')} className="text-accent hover:underline">
            Mark done
          </button>
        )}
        {r.status === 'done' && c.can_confirm && (
          <button onClick={() => a.set(r.key, 'confirmed')} className="text-accent hover:underline">
            Confirm
          </button>
        )}
        {r.status === 'done' && c.can_mark && (
          <button onClick={() => a.set(r.key, 'open')} className="text-ink-3 hover:underline">
            Undo
          </button>
        )}
        {r.status === 'confirmed' && !r.auto && c.can_confirm && (
          <button onClick={() => a.set(r.key, 'done')} className="text-ink-3 hover:underline">
            Reopen
          </button>
        )}
        {r.status === 'open' && a.proposed.has(r.target) && <span className="font-normal text-soon">Waiting for HR</span>}
      </span>
    </li>
  )
}

export function LetterView({ letter }: { letter: Letter }) {
  return (
    <article className="document mx-auto max-w-[640px] rounded-[6px] bg-page p-10 text-[15px] leading-6 shadow-card print:shadow-none">
      <div className="mb-8 flex items-center justify-between">
        <img src="/logo-mark.png" alt="" className="h-7 w-auto" />
        <span className="text-ink-2">{letter.date}</span>
      </div>
      <p className="mb-6">To {letter.to}</p>
      <h3 className="mb-4 font-semibold">{letter.subject}</h3>
      {letter.body.map((p) => (
        <p key={p} className="mb-4">
          {p}
        </p>
      ))}
      <div className="mt-10">
        <div className="mb-8 h-px w-48 bg-strong" />
        <div className="font-medium">{letter.signatory.name}</div>
        <div className="text-ink-2">{letter.signatory.title}</div>
      </div>
    </article>
  )
}

export function ClearanceView({ h, successorActive }: { h: Handover; successorActive: boolean }) {
  const id = h.id
  const { data: c, error, reload } = useApi<Clearance>(`/handovers/${encodeURIComponent(id)}/clearance`)
  const [failed, setFailed] = useState('')
  if (error) return <ErrorNote message={error} />
  if (!c) return <Loading />

  async function set(key: string, status: Row['status']) {
    setFailed('')
    try {
      await api.post(`/handovers/${encodeURIComponent(id)}/clearance`, { key, status })
      reload()
    } catch (e) {
      setFailed(e instanceof Error ? e.message : 'Failed')
    }
  }

  async function hand(r: Row) {
    setFailed('')
    try {
      if (r.key.startsWith('admin:')) await api.post(`/handovers/${encodeURIComponent(id)}/accounts/${encodeURIComponent(r.target)}/reassign`, {})
      else await api.post(`/responsibilities/${encodeURIComponent(r.target)}/backup`, { employee_id: h.successor_id })
      reload()
    } catch (e) {
      setFailed(e instanceof Error ? e.message : 'Failed')
    }
  }

  async function decide(p: Proposal, approve: boolean) {
    setFailed('')
    try {
      await api.post(`/reassignments/${encodeURIComponent(p.id)}/decide`, { approve })
      reload()
    } catch (e) {
      setFailed(e instanceof Error ? e.message : 'Failed')
    }
  }

  const actions: Actions = { set, hand, successor: h.successor, successorActive, proposed: new Set(c.proposals.map((p) => p.account)) }
  const groups = [...new Set(c.items.map((r) => r.group))]
  return (
    <div className="flex flex-col gap-4">
      {failed && <ErrorNote message={failed} />}
      {c.proposals.length > 0 && (
        <Card className="print:hidden">
          <CardHeader title="Account handovers to approve" meta={c.proposals.length} />
          <ul className="flex flex-col divide-y divide-line">
            {c.proposals.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-2.5">
                <span className="min-w-0">
                  <span className="block text-[14px] font-medium">
                    {p.account_name} → {p.to_name}
                  </span>
                  <span className="block text-[13px] text-ink-3">
                    Proposed by {p.proposed_by}
                    {p.note ? ` · ${p.note}` : ''}. {first(h.employee)} keeps access until the last day.
                  </span>
                </span>
                {c.can_confirm ? (
                  <span className="flex gap-2">
                    <Button variant="secondary" onClick={() => void decide(p, true)}>
                      Approve
                    </Button>
                    <Button variant="ghost" onClick={() => void decide(p, false)}>
                      Reject
                    </Button>
                  </span>
                ) : (
                  <Chip tone="soon">Waiting for HR</Chip>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card className="print:hidden">
        <CardHeader
          title="Clearance"
          meta={`${c.confirmed}/${c.total}`}
          right={c.complete ? <Chip tone="ok">Cleared</Chip> : <Chip tone="soon">{c.total - c.confirmed} left</Chip>}
        />
        <div className="mb-2">
          <Bar value={c.confirmed} max={Math.max(1, c.total)} />
        </div>
        {groups.map((g) => {
          const rows = c.items.filter((r) => r.group === g)
          return (
            <section key={g} className="mt-4">
              <h3 className="flex items-center justify-between text-[13px] font-medium text-ink-3">
                {g}
                <span className="num">
                  {rows.filter((r) => r.status === 'confirmed').length}/{rows.length}
                </span>
              </h3>
              <ul className="flex flex-col divide-y divide-line">
                {rows.map((r) => (
                  <RowView key={r.key} r={r} c={c} a={actions} />
                ))}
              </ul>
            </section>
          )
        })}
      </Card>

      <LetterSection h={h} c={c} onChange={reload} />
    </div>
  )
}

/** HR's final sign-off: the relieving letter, sent by email on (or after) the last day. */
function LetterSection({ h, c, onChange }: { h: Handover; c: Clearance; onChange: () => void }) {
  const [subject, setSubject] = useState(c.email_draft?.subject ?? '')
  const [body, setBody] = useState(c.email_draft?.body ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState('')

  async function send(when: 'now' | 'last_day') {
    setBusy(true)
    setError('')
    try {
      const r = await api.post<{ emailed?: boolean; to?: string; scheduled?: boolean; at?: number }>(`/handovers/${encodeURIComponent(h.id)}/letter`, { subject, body, when })
      setDone(r.scheduled ? `Scheduled for ${date(r.at ?? h.effective_at, true)}. It goes out automatically.` : r.emailed ? `Sent to ${r.to}.` : 'Recorded as sent. Email is not set up, so share the PDF.')
      onChange()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  if (!c.letter) {
    return (
      <Card className="print:hidden">
        <div className="flex items-center gap-3 text-[14px] text-ink-2">
          <Lock size={18} className="text-ink-3" />
          <span>
            <span className="font-medium text-ink">Relieving letter</span> ·{' '}
            {c.complete && c.transferred ? `HR sends it on the last day, ${date(h.effective_at, true)}.` : c.letter_gate.reason.replace('Ready when', 'ready when')}
          </span>
        </div>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <h2 className="text-[16px] font-semibold">
          Relieving letter{' '}
          {c.letter_sent_at ? (
            <Chip tone="ok">Sent {date(c.letter_sent_at, true)}</Chip>
          ) : c.letter_scheduled_at ? (
            <Chip tone="accent">Scheduled for {date(c.letter_scheduled_at, true)}</Chip>
          ) : null}
        </h2>
        <Button variant="secondary" onClick={() => window.print()}>
          <Printer size={15} /> Print or save as PDF
        </Button>
      </div>
      {c.email_draft && !c.letter_sent_at && (
        <Card className="print:hidden">
          <CardHeader title="Email to send" right={c.email_draft.to || 'No email on file'} />
          <div className="flex flex-col gap-2.5">
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Subject" className="w-full" />
            <TextArea rows={8} value={body} onChange={(e) => setBody(e.target.value)} aria-label="Email" />
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => void send('now')} disabled={busy || !c.letter_gate.can_send} title={c.letter_gate.can_send ? undefined : c.letter_gate.reason}>
                Send now
              </Button>
              {!c.letter_gate.can_send && c.letter_gate.ready_at && (
                <Button variant="secondary" onClick={() => void send('last_day')} disabled={busy}>
                  Send on {date(c.letter_gate.ready_at, true)}
                </Button>
              )}
              {!c.letter_gate.can_send && <span className="text-[13px] text-ink-3">{c.letter_gate.reason}</span>}
            </div>
            {done && <p className="text-[13px] text-ok-text">{done}</p>}
            {error && <p className="text-[13px] text-risk-text">{error}</p>}
          </div>
        </Card>
      )}
      <LetterView letter={c.letter} />
    </div>
  )
}
