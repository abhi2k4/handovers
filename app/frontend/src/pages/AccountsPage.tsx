import { useState } from 'react'
import { Link } from 'react-router'
import { StatBand } from '../components/StatBand'
import { Button, Card, CardHeader, ErrorNote, PageHeader, PageSkeleton } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { date, daysBetween, first } from '../lib/format'
import type { Person } from '../types/api'

interface HandoverRow {
  id: string
  status: string
  employee_id: string
  employee: string
  successor: string | null
  effective_at: number
}

/** IT: accounts only a leaver administers, across open handovers. Access first. */
export function AccountsPage() {
  const { data: handovers, error, loading } = useApi<HandoverRow[]>('/handovers')
  const open = (handovers ?? []).filter((h) => h.status !== 'transferred')

  if (loading && !handovers) return <PageSkeleton />
  if (error) return <ErrorNote message={error} />

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Accounts to reassign" sub="Accounts where someone who is leaving is the only admin. Give each one to the successor before the last day." />
      {open.length === 0 && <p className="text-ink-3">No open handovers.</p>}
      {open.map((h) => (
        <LeaverAccounts key={h.id} h={h} />
      ))}
    </div>
  )
}

function LeaverAccounts({ h }: { h: HandoverRow }) {
  const { data: p, reload } = useApi<Person>(`/people/${encodeURIComponent(h.employee_id)}`)
  const { data: meta } = useApi<{ now: number }>('/meta')
  const sole = (p?.accounts ?? []).filter((a) => a.other_admins.length === 0)
  const shared = (p?.accounts ?? []).length - sole.length
  const days = meta ? daysBetween(meta.now, h.effective_at) : null

  return (
    <Card>
      <CardHeader
        title={h.employee}
        meta={`last day ${date(h.effective_at, true)}`}
        right={<Link to={`/handovers/${encodeURIComponent(h.id)}?tab=plan`} className="text-accent">Handover plan</Link>}
      />
      <div className="mb-4">
        <StatBand
          variant="band"
          figures={[
            { label: 'Only admin', value: sole.length, tone: sole.length ? 'text-risk-text' : 'text-ok-text' },
            { label: 'Shared admin', value: shared },
            { label: 'Days left', value: days ?? '–', tone: days !== null && days < 7 ? 'text-risk-text' : undefined },
          ]}
        />
      </div>
      <ul className="flex flex-col divide-y divide-line">
        {sole.map((a) => (
          <li key={a.id} className="flex items-center justify-between gap-4 py-2.5">
            <span>
              <span className="font-medium">{a.name}</span>
              <span className="text-ink-3"> · {a.system} · {a.role}</span>
            </span>
            <ReassignButton hid={h.id} aid={a.id} successor={h.successor} onDone={reload} />
          </li>
        ))}
      </ul>
      {p && sole.length === 0 && <p className="text-ink-3">Every account {first(h.employee)} administers has another admin.</p>}
    </Card>
  )
}

function ReassignButton({ hid, aid, successor, onDone }: { hid: string; aid: string; successor: string | null; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [proposed, setProposed] = useState(false)

  async function reassign() {
    setBusy(true)
    setFailure(null)
    try {
      const r = await api.post<{ status: string }>(`/handovers/${encodeURIComponent(hid)}/accounts/${encodeURIComponent(aid)}/reassign`, {})
      // IT and managers propose; HR approves. HR's own reassignment applies at once.
      if (r.status === 'proposed') {
        setProposed(true)
        setBusy(false)
      } else onDone()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Something went wrong')
      setBusy(false)
    }
  }

  if (!successor) return <span className="text-[13px] text-ink-3">Choose a successor first</span>
  if (proposed) return <span className="text-[13px] text-soon">Proposed · waiting for HR</span>
  return (
    <span className="flex shrink-0 items-center gap-2">
      {failure && <span className="text-[13px] text-risk-text">{failure}</span>}
      <Button disabled={busy} onClick={() => void reassign()}>
        {busy ? 'Reassigning…' : `Give admin to ${first(successor)}`}
      </Button>
    </span>
  )
}
