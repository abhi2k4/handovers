import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { date, first } from '../lib/format'
import { KINDS } from '../lib/orgRisk'
import { successorOptions } from '../lib/successors'
import type { Handover, PersonRow } from '../types/api'
import { useConfirmable } from './Confirm'
import { Button, Modal, Select } from './ui'

const DAY = 86_400_000

/** Start an exit in one step: who, notice period, successor, and what only they hold. */
export function StartExit({ now, onClose }: { now: number; onClose: () => void }) {
  const navigate = useNavigate()
  const { data: people } = useApi<PersonRow[]>('/people')
  const [who, setWho] = useState('')
  const [notice, setNotice] = useState(30)
  const [successor, setSuccessor] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const active = (people ?? []).filter((p) => p.status === 'active' && !p.handover_id)
  const person = active.find((p) => p.id === who)
  const successors = successorOptions(people ?? [], person ?? null)
  const { run, dialog } = useConfirmable()

  async function start() {
    setBusy(true)
    setError('')
    try {
      const h = await run((confirmed) =>
        api.post<Handover>('/handovers', { employee_id: who, successor_id: successor || null, notice_days: notice, confirmed }),
      )
      if (h) navigate(`/handovers/${encodeURIComponent(h.id)}`)
      else setBusy(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
      setBusy(false)
    }
  }

  return (
    <>
    {dialog}
    <Modal
      title="Start handover"
      onClose={onClose}
      footer={
        <>
          {error && <span className="mr-auto text-[13px] text-risk-text">{error}</span>}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={start} disabled={!who || busy}>
            {busy ? 'Starting…' : 'Start handover'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4 text-[14px]">
        <label className="flex flex-col gap-1.5">
          <span className="font-medium">Who is leaving?</span>
          <Select value={who} onChange={(e) => setWho(e.target.value)} aria-label="Who is leaving">
            <option value="">Choose a person</option>
            {active.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.title}
              </option>
            ))}
          </Select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1.5">
            <span className="font-medium">Notice period</span>
            <Select value={notice} onChange={(e) => setNotice(Number(e.target.value))} aria-label="Notice period">
              {[15, 30, 60, 90].map((d) => (
                <option key={d} value={d}>
                  {d} days
                </option>
              ))}
            </Select>
          </label>
          <div className="flex flex-col gap-1.5">
            <span className="font-medium">Last day</span>
            <span className="num flex h-9 items-center">{date(now + notice * DAY)}</span>
          </div>
        </div>
        <label className="flex flex-col gap-1.5">
          <span className="font-medium">Successor</span>
          <Select value={successor} onChange={(e) => setSuccessor(e.target.value)} aria-label="Successor">
            <option value="">Decide later</option>
            {successors.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.status === 'incoming' ? ' (joining)' : ''}
                {person && (p.sameTeam ? ' · same team' : ` · ${p.team}`)}
              </option>
            ))}
          </Select>
        </label>

        {person && (
          <div className="rounded-[6px] bg-app p-4">
            <div className="mb-3 font-medium">
              {person.risk > 0 ? `${person.risk} things only ${first(person.name)} holds` : `Nothing rests on ${first(person.name)} alone`}
            </div>
            <div className="grid grid-cols-4 gap-2">
              {KINDS.map((k) => (
                <div key={k.key}>
                  <div className={`num text-[20px] font-semibold ${(person.sole[k.key] ?? 0) > 0 ? 'text-risk-text' : 'text-ink-3'}`}>
                    {person.sole[k.key] ?? 0}
                  </div>
                  <div className="text-[12px] text-ink-3">{k.label}</div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[13px] text-ink-2">
              Starting builds the handover plan, the exit interview and the clearance list from this.
            </p>
          </div>
        )}
      </div>
    </Modal>
    </>
  )
}
