import { X } from './icons'
import { useNavigate } from 'react-router'
import { Avatar, Button, Sheet } from './ui'
import { useApi } from '../hooks/useApi'
import { CADENCE, first } from '../lib/format'
import { type DashHandover, KINDS, type RiskPerson } from '../lib/orgRisk'

interface Simulation {
  responsibilities: { id: string; title: string; cadence: string | null }[]
  accounts: { id: string; title: string }[]
  relationships: { id: string; title: string }[]
  knowledge: { id: string; title: string; kind: string }[]
}

/** One segment per readiness check; hovering a segment names it. */
export function Readiness({ h }: { h: DashHandover }) {
  const done = h.steps.filter((s) => s.done).length
  return (
    <span className="flex items-center gap-2" aria-label={`${done} of ${h.steps.length} checks done`}>
      <span className="flex gap-0.5">
        {h.steps.map((s) => (
          <span key={s.key} title={`${s.label}: ${s.done ? 'done' : 'open'}`} className={`h-1.5 w-4 rounded-[1px] ${s.done ? 'bg-ok' : 'bg-hover'}`} />
        ))}
      </span>
      <span className="num text-[13px] text-ink-3">
        {done}/{h.steps.length} ready
      </span>
    </span>
  )
}

export function Legend() {
  return (
    <span className="flex flex-wrap items-center gap-3">
      {KINDS.map((k) => (
        <span key={k.key} className="flex items-center gap-1.5">
          <span className="size-2 rounded-[2px]" style={{ background: k.color }} />
          {k.label}
        </span>
      ))}
    </span>
  )
}

/** "If they left today": what only this person holds. `actions` adds Open memory and Start handover (HR). */
export function SimulationSheet({ person, onClose, actions = true }: { person: RiskPerson; onClose: () => void; actions?: boolean }) {
  const { data } = useApi<Simulation>(`/people/${encodeURIComponent(person.id)}/simulate`)
  const navigate = useNavigate()
  const groups = data
    ? [
        { label: 'Accounts', items: data.accounts.map((a) => ({ id: a.id, title: a.title, sub: 'No other admin' })) },
        { label: 'Work', items: data.responsibilities.map((r) => ({ id: r.id, title: r.title, sub: r.cadence ? CADENCE[r.cadence] : '' })) },
        { label: 'Contacts', items: data.relationships.map((r) => ({ id: r.id, title: r.title, sub: 'No other contact' })) },
        { label: 'Knowledge', items: data.knowledge.map((k) => ({ id: k.id, title: k.title, sub: k.kind })) },
      ]
    : []
  return (
    <Sheet onClose={onClose}>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Avatar name={person.name} size={40} />
          <div>
            <div className="text-[17px] font-semibold">{person.name}</div>
            <div className="text-[13px] text-ink-3">{person.title}</div>
          </div>
        </div>
        <button onClick={onClose} aria-label="Close" className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-ink">
          <X size={18} />
        </button>
      </div>
      <div className="mb-3 text-[14px] font-medium text-ink-2">{person.leaving ? `Only ${first(person.name)} holds today` : `If ${first(person.name)} left today`}</div>
      <div className="mb-6 grid grid-cols-4 gap-2">
        {KINDS.map((k) => (
          <div key={k.key} className="rounded-[6px] bg-app px-3 py-2.5">
            <div className="num text-[20px] leading-6 font-semibold">{data ? data[k.key].length : (person.sole[k.key] ?? 0)}</div>
            <div className="text-[12px] text-ink-3">{k.label}</div>
          </div>
        ))}
      </div>
      {!data ? (
        <div className="text-[14px] text-ink-3">Loading…</div>
      ) : (
        <div className="flex flex-1 flex-col gap-5">
          {groups
            .filter((g) => g.items.length)
            .map((g) => (
              <div key={g.label}>
                <div className="mb-1 text-[13px] font-medium text-ink-3">{g.label}</div>
                <ul>
                  {g.items.map((i) => (
                    <li key={i.id} className="flex items-baseline justify-between gap-4 border-b border-line py-2 text-[14px] last:border-0">
                      <span className="min-w-0">{i.title}</span>
                      <span className="shrink-0 text-[13px] text-ink-3">{i.sub}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      )}
      {actions && (
        <div className="sticky bottom-0 -mx-6 mt-6 flex gap-2 border-t border-line bg-page px-6 pt-4">
          <Button variant="secondary" className="flex-1" onClick={() => navigate(`/people/${encodeURIComponent(person.id)}`)}>
            Open memory
          </Button>
          {!person.leaving && (
            <Button className="flex-1" onClick={() => navigate(`/people/${encodeURIComponent(person.id)}#handover`)}>
              Start handover
            </Button>
          )}
        </div>
      )}
    </Sheet>
  )
}
