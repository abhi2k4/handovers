import { useState } from 'react'
import { Link } from 'react-router'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import type { Person, PersonRow } from '../types/api'
import { Button, Card, CardHeader, Empty, Select } from './ui'

/**
 * "Reduce key-person risk": work only one teammate does, with a backup picker. Fixing this before
 * anyone resigns is the cheapest handover there is. Leavers are excluded: their handover covers them.
 */
export function BackupsCard({ team, me, onChange }: { team: PersonRow[]; me: { id: string; name: string }; onChange: () => void }) {
  const owners = team.filter((p) => p.status === 'active' && !p.handover_id && (p.sole.responsibilities ?? 0) > 0)
  const candidates = [...team.filter((p) => p.status === 'active' && !p.handover_id), { id: me.id, name: `${me.name} (you)` }]
  const total = owners.reduce((n, p) => n + (p.sole.responsibilities ?? 0), 0)

  return (
    <Card>
      <CardHeader title="Reduce key-person risk" meta={total} />
      <p className="mb-3 text-[13px] text-ink-3">Work only one teammate does today. Add a backup so nothing stops if they leave or take leave.</p>
      {owners.length === 0 ? (
        <Empty>Every responsibility on your team has a backup.</Empty>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {owners.map((p) => (
            <OwnerRows key={p.id} owner={p} candidates={candidates.filter((c) => c.id !== p.id)} onChange={onChange} />
          ))}
        </ul>
      )}
    </Card>
  )
}

function OwnerRows({ owner, candidates, onChange }: { owner: PersonRow; candidates: { id: string; name: string }[]; onChange: () => void }) {
  const { data: p, reload } = useApi<Person>(`/people/${encodeURIComponent(owner.id)}`)
  const sole = (p?.responsibilities ?? []).filter((r) => r.co_owners.length === 0)
  return (
    <>
      {sole.map((r) => (
        <BackupRow key={r.id} rid={r.id} title={r.title} owner={owner} candidates={candidates} onDone={() => {
            reload()
            onChange()
          }} />
      ))}
    </>
  )
}

function BackupRow({
  rid,
  title,
  owner,
  candidates,
  onDone,
}: {
  rid: string
  title: string
  owner: PersonRow
  candidates: { id: string; name: string }[]
  onDone: () => void
}) {
  const [pick, setPick] = useState('')
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  async function assign() {
    setBusy(true)
    setFailure(null)
    try {
      await api.post(`/responsibilities/${encodeURIComponent(rid)}/backup`, { employee_id: pick })
      onDone()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Something went wrong')
      setBusy(false)
    }
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-2.5">
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px]">{title}</span>
        <span className="block text-[13px] text-ink-3">
          Only{' '}
          <Link to={`/people/${encodeURIComponent(owner.id)}`} className="hover:text-accent">
            {owner.name}
          </Link>
          {failure && <span className="text-risk-text"> · {failure}</span>}
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        <Select value={pick} onChange={(e) => setPick(e.target.value)} aria-label={`Backup for ${title}`} disabled={busy}>
          <option value="">Choose backup…</option>
          {candidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Button disabled={!pick || busy} onClick={() => void assign()}>
          {busy ? 'Adding…' : 'Add backup'}
        </Button>
      </span>
    </li>
  )
}
