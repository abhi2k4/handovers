import { ArrowRight } from '../../components/icons'
import { useState } from 'react'
import { Link } from 'react-router'
import { Button, Empty, ErrorNote, Loading, Section, Select, TextArea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useViewAs } from '../../hooks/useViewAs'
import { api } from '../../lib/api'
import { date, first } from '../../lib/format'
import type { Handover, PersonRow } from '../../types/api'

interface Preview {
  ready: boolean
  reason?: string
  successor?: string
  include: { id: string; kind: string; title: string; reason: string }[]
  exclude: { id: string; kind: string; title: string; reason: string }[]
  responsibilities: string[]
  relationships: string[]
  open_questions: number
  /** Already approved once: `include` is then only what was captured since. */
  transferred?: boolean
}

interface Result {
  followup?: boolean
  knowledge: number
  responsibilities: number
  relationships: number
  excluded: number
}

export function TransferView({ h, people, onChange }: { h: Handover; people: PersonRow[]; onChange: () => void }) {
  const { data: p, error, loading, reload } = useApi<Preview>(`/handovers/${encodeURIComponent(h.id)}/transfer`)
  const [approver, setApprover] = useState(h.approver?.id ?? h.manager_id ?? '')
  const [rejecting, setRejecting] = useState(false)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const { persona, me } = useViewAs()
  // The one approver: the manager, or the next one up when the manager is away (h.approver).
  const isManager = h.can?.approve ?? (!persona || (me?.reports.includes(h.employee_id) ?? false))
  const approverName = h.approver?.name ?? h.manager ?? 'the manager'
  const rejected = h.transfer?.decision === 'rejected' && h.status !== 'transferred'

  if (loading && !p) return <Loading />
  if (error || !p) return <ErrorNote message={error ?? 'Failed'} />

  async function approve() {
    setBusy(true)
    setErr(null)
    try {
      setResult(await api.post<Result>(`/handovers/${encodeURIComponent(h.id)}/transfer`, { approved_by: approver || (me?.id ?? '') }))
      onChange()
      reload()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function reject() {
    setBusy(true)
    setErr(null)
    try {
      await api.post(`/handovers/${encodeURIComponent(h.id)}/transfer/reject`, { comment })
      setRejecting(false)
      setComment('')
      onChange()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  if (h.status === 'transferred' || result) {
    const followup = p.transferred ? p.include : []
    return (
      <div className="max-w-[40rem]">
        <p className="text-[18px] leading-[26px] tracking-[-0.01em]">
          Handed over to {h.successor}
          <span className="text-ink-2">
            {h.transfer?.approved_by ? `, approved by ${h.transfer.approved_by}` : ''}
            {h.transfer?.approved_at ? ` on ${date(h.transfer.approved_at)}` : ''}.
          </span>
        </p>
        {h.employee_status !== 'departed' && (
          <p className="mt-2 text-[14px] text-ink-3">
            {first(h.employee)} keeps working, and can still answer questions, until {date(h.effective_at, true)}. Anything new is sent to {first(h.successor)} as a follow-up.
          </p>
        )}
        {result && !result.followup && (
          <p className="mt-3 text-[14px] text-ink-2">
            <span className="num text-ink">{result.knowledge}</span> pieces of knowledge,{' '}
            <span className="num text-ink">{result.responsibilities}</span> responsibilities and{' '}
            <span className="num text-ink">{result.relationships}</span> relationships moved.{' '}
            <span className="num text-ink">{result.excluded}</span> stayed private.
          </p>
        )}
        {result?.followup && (
          <p className="mt-3 text-[14px] text-ink-2">
            <span className="num text-ink">{result.knowledge}</span> more {result.knowledge === 1 ? 'item' : 'items'} sent to {first(h.successor)}.
          </p>
        )}
        {followup.length > 0 && (
          <div className="mt-8">
            <Section title="New since approval" meta={followup.length}>
              <p className="mb-3 text-[14px] text-ink-2">
                {first(h.employee)} captured this after the transfer was approved. {first(h.successor)} does not have it yet.
              </p>
              <ul className="border-t border-line">
                {followup.map((i) => (
                  <li key={i.id} className="grid grid-cols-[72px_minmax(0,1fr)] gap-4 border-b border-line py-2.5 text-[14px]">
                    <span className="text-[13px] text-ink-3">{i.kind}</span>
                    <span className="min-w-0 truncate">{i.title}</span>
                  </li>
                ))}
              </ul>
              {isManager ? (
                <Button className="mt-4" onClick={approve} disabled={busy}>
                  {busy ? 'Sending…' : `Approve and send to ${first(h.successor)}`}
                </Button>
              ) : (
                <p className="mt-3 text-[13px] text-ink-3">Waiting for {approverName} to approve.</p>
              )}
              {err && <p className="mt-2 text-[13px] text-risk-text">{err}</p>}
            </Section>
          </div>
        )}
        <Link to={`/ask?as=${encodeURIComponent(h.successor_id ?? '')}`} className="mt-6 inline-block">
          <Button>
            Ask as {first(h.successor)} <ArrowRight size={13} />
          </Button>
        </Link>
      </div>
    )
  }

  if (!p.ready) return <Empty>{p.reason}</Empty>

  return (
    <div className="flex flex-col gap-12">
      {rejected && (
        <div className="rounded-[6px] bg-soon-soft px-4 py-3 text-[14px] text-ink">
          <span className="font-medium">Sent back by {h.transfer?.approved_by}</span>
          {h.transfer?.approved_at ? <span className="text-ink-2"> on {date(h.transfer.approved_at, true)}</span> : null}
          {h.transfer?.comment && <p className="mt-1 text-ink-2">“{h.transfer.comment}”</p>}
        </div>
      )}
      <p className="max-w-[40rem] text-[16px] leading-6 text-ink-2">
        {first(p.successor)} gets the same knowledge {first(h.employee)} holds, linked back to where it came from and who
        approved it. Nothing is copied, and the transfer can be revoked.
      </p>

      <Section title={`Moves to ${p.successor}`} meta={p.include.length}>
        <ul className="border-t border-line">
          {p.include.map((i) => (
            <li key={i.id} className="grid grid-cols-[72px_minmax(0,1fr)_auto] gap-4 border-b border-line py-2.5 text-[14px]">
              <span className="text-[13px] text-ink-3">{i.kind}</span>
              <span className="min-w-0 truncate">{i.title}</span>
              <span className="text-[13px] text-ink-3">{i.reason === 'history' ? 'History' : ''}</span>
            </li>
          ))}
        </ul>
        <div className="mt-6 grid gap-8 sm:grid-cols-2">
          <div>
            <div className="mb-2 text-[13px] text-ink-3">Responsibilities</div>
            <ul className="flex flex-col gap-1 text-[14px]">
              {p.responsibilities.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="mb-2 text-[13px] text-ink-3">Relationships</div>
            <ul className="flex flex-col gap-1 text-[14px]">
              {p.relationships.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      <Section title={`Stays with ${first(h.employee)}`} meta={p.exclude.length}>
        {p.exclude.length === 0 ? (
          <Empty>Nothing is held back.</Empty>
        ) : (
          <ul className="border-t border-line">
            {p.exclude.map((i) => (
              <li key={i.id} className="flex justify-between gap-4 border-b border-line py-2.5 text-[14px]">
                <span className="text-ink-2">{i.reason === 'personal' ? 'Personal note' : i.title}</span>
                <span className="text-[13px] text-ink-3 capitalize">{i.reason}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-6">
        {!isManager ? (
          <span className="text-[14px] text-ink-2">
            Waiting for {approverName} to approve
            {h.approver && h.approver.via !== 'manager' ? ` (${h.approver.via === 'hr' ? 'HR approves: there is no manager to ask' : `${h.manager ?? 'the manager'} is away or leaving`})` : ''}.
          </span>
        ) : rejecting ? (
          <div className="flex w-full flex-col gap-2">
            <TextArea rows={2} placeholder="What needs to change before you approve?" value={comment} onChange={(e) => setComment(e.target.value)} />
            <div className="flex gap-2">
              <Button variant="secondary" onClick={reject} disabled={busy || comment.trim().length < 5}>
                {busy ? 'Sending…' : 'Send back'}
              </Button>
              <Button variant="ghost" onClick={() => setRejecting(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <>
            {persona ? (
              <span className="text-[14px] text-ink-2">Approving as {me?.name}</span>
            ) : (
              // Unrestricted mode only: say who approves. With "View as", the server records the viewer.
              <Select value={approver} onChange={(e) => setApprover(e.target.value)} aria-label="Approved by">
                <option value="">Approved by…</option>
                {people
                  .filter((x) => x.status === 'active' && x.id !== h.employee_id)
                  .map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name}
                    </option>
                  ))}
              </Select>
            )}
            <Button onClick={approve} disabled={busy || (!persona && !approver)}>
              {busy ? 'Transferring…' : 'Approve and transfer'}
            </Button>
            <Button variant="ghost" onClick={() => setRejecting(true)} disabled={busy}>
              Send back
            </Button>
          </>
        )}
        {p.open_questions > 0 && (
          <span className="text-[13px] text-soon">
            {p.open_questions} exit interview {p.open_questions === 1 ? 'question is' : 'questions are'} still open
          </span>
        )}
        {err && <p className="w-full text-[13px] text-risk-text">{err}</p>}
      </div>
    </div>
  )
}
