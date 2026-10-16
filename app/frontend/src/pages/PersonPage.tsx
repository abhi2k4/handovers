import { Lock, Plus } from '../components/icons'
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router'
import { StatBand } from '../components/StatBand'
import { Avatar, Bar, Breadcrumb, Button, Card, CardHeader, Chip, Empty, ErrorNote, PageHeader, PageSkeleton, Select } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { useViewAs } from '../hooks/useViewAs'
import { api } from '../lib/api'
import { CADENCE, date, first, pct, plural } from '../lib/format'
import { useConfirmable } from '../components/Confirm'
import { successorOptions } from '../lib/successors'
import type { Handover, Person, PersonRow } from '../types/api'

function StartHandover({ person, people }: { person: Person; people: PersonRow[] }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(useLocation().hash === '#handover')
  const [successor, setSuccessor] = useState('')
  const [notice, setNotice] = useState(30)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sorted = successorOptions(people, { id: person.id, team: person.team, team_id: person.team_id })
  const { run, dialog } = useConfirmable()

  if (!open)
    return (
      <Button onClick={() => setOpen(true)}>
        <Plus size={14} strokeWidth={2} /> Start handover
      </Button>
    )

  async function start() {
    setBusy(true)
    setError(null)
    try {
      const h = await run((confirmed) =>
        api.post<Handover>('/handovers', { employee_id: person.id, successor_id: successor || null, notice_days: notice, confirmed }),
      )
      if (h) navigate(`/handovers/${encodeURIComponent(h.id)}`)
      else setBusy(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select value={notice} onChange={(e) => setNotice(Number(e.target.value))} aria-label="Notice period">
        {[15, 30, 60, 90].map((d) => (
          <option key={d} value={d}>
            {d}-day notice
          </option>
        ))}
      </Select>
      <Select value={successor} onChange={(e) => setSuccessor(e.target.value)} aria-label="Successor">
        <option value="">Successor not decided</option>
        {sorted.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
            {p.status === 'incoming' ? ' (joining)' : ''}
            {p.sameTeam ? '' : ` · ${p.team}`}
          </option>
        ))}
      </Select>
      {dialog}
      <Button onClick={start} disabled={busy}>
        {busy ? 'Starting…' : 'Start'}
      </Button>
      <Button variant="ghost" onClick={() => setOpen(false)}>
        Cancel
      </Button>
      {error && <p className="w-full text-[13px] text-risk-text">{error}</p>}
    </div>
  )
}

function Numbers({ p, self }: { p: Person; self: boolean }) {
  const alone = p.responsibilities.filter((r) => r.co_owners.length === 0).length
  const admin = p.accounts.filter((a) => ['admin', 'owner'].includes(a.role) && a.other_admins.length === 0)
  const contacts = p.stakeholders.filter((s) => s.other_contacts.length === 0)
  return (
    <div className="mb-4">
      <StatBand
        figures={[
          { label: 'Learned from', value: p.sources, note: 'work records' },
          { label: self ? 'Work only you do' : 'Work only they do', value: alone, note: `of ${p.responsibilities.length}`, tone: alone ? 'text-risk-text' : undefined },
          { label: 'Only admin of', value: admin.length, note: admin.map((a) => a.name).join(', ') || undefined, tone: admin.length ? 'text-risk-text' : undefined },
          {
            label: 'Only contact for',
            value: contacts.length,
            note: contacts.map((c) => c.name).join(', ') || undefined,
            tone: contacts.length ? 'text-risk-text' : undefined,
          },
        ]}
      />
    </div>
  )
}

function KnowledgeRow({ k, personId, onChange, self }: { k: Person['knowledge'][number]; personId: string; onChange: () => void; self: boolean }) {
  const personal = k.sensitivity === 'personal'
  const superseded = k.status === 'superseded'
  async function toggle() {
    await api.post(`/people/${encodeURIComponent(personId)}/knowledge/${encodeURIComponent(k.id)}/private`, { private: !k.private })
    onChange()
  }
  const notes: string[] = []
  if (superseded) notes.push('Replaced')
  else if (!personal) {
    if (k.via === 'transfer') notes.push('Inherited')
    else if (k.others.length === 0) notes.push(self ? 'Only you' : 'Only them')
    if (k.kind !== 'Claim' && !k.documented) notes.push('Not written down')
    if (k.kind === 'Claim' && !k.justified_by && k.others.length === 0) notes.push('No reason recorded')
    if (k.private) notes.push('Private')
  }
  return (
    <li className="group grid grid-cols-[72px_minmax(0,1fr)_auto] gap-4 border-b border-line py-3 last:border-0">
      <span className="text-[13px] leading-5 text-ink-3">{k.kind}</span>
      {personal ? (
        <span className="flex items-center gap-1.5 text-[14px] leading-5 text-ink-3">
          <Lock size={12} strokeWidth={1.75} /> {self ? 'Personal note, only you can see it' : 'Personal note, hidden from everyone else'}
        </span>
      ) : (
        <div className="min-w-0">
          <div className={`text-[14px] leading-5 font-medium ${superseded ? 'text-ink-3 line-through decoration-strong' : ''}`}>{k.title}</div>
          {(k.rationale || (k.steps && k.steps.length > 0)) && (
            <p className="mt-0.5 text-[13px] leading-[18px] text-ink-2">{k.rationale ?? k.steps?.join(' · ')}</p>
          )}
          {notes.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {notes.map((n) => (
                <Chip key={n} tone={n === 'Only them' || n === 'Only you' || n === 'No reason recorded' ? 'risk' : n === 'Not written down' ? 'soon' : 'idle'}>
                  {n}
                </Chip>
              ))}
            </div>
          )}
        </div>
      )}
      {personal ? (
        <span />
      ) : (
        <button onClick={toggle} className={`self-start text-[13px] leading-5 ${k.private ? 'text-ink' : 'text-ink-3 hover:text-ink'}`}>
          {k.private ? 'Make shareable' : 'Keep private'}
        </button>
      )}
    </li>
  )
}

/** A person's memory. `self`: the same page for yourself ("My memory", at /me), written to you. */
export function PersonPage({ self }: { self?: string } = {}) {
  const params = useParams()
  const { persona } = useViewAs()
  const id = self ?? params.id ?? ''
  const { data: p, error, loading, reload } = useApi<Person>(`/people/${encodeURIComponent(id)}`)
  const { data: people } = useApi<PersonRow[]>('/people')
  // Your own page lives at /me, so the sidebar shows where you are.
  if (!self && persona && id === persona) return <Navigate to="/me" replace />
  if (loading && !p) return <PageSkeleton />
  if (error || !p) return <ErrorNote message={error ?? 'Not found'} />
  const you = !!self
  const row = people?.find((x) => x.id === p.id)
  const name = first(p.name)
  const only = you ? 'Only you' : `Only ${name}`
  const knowledge = [...p.knowledge].sort((a, b) => Number(a.sensitivity === 'personal') - Number(b.sensitivity === 'personal'))

  return (
    <>
      {you ? (
        <PageHeader
          title="My memory"
          sub={`What Handovers has learned from your work: ${p.title} · ${p.team}${p.manager ? ` · reports to ${p.manager}` : ''}. Personal notes stay yours; you choose what else is shared.`}
          right={
            row?.handover_id ? (
              <Link to="/">
                <Button variant="secondary">Your handover</Button>
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
      <Breadcrumb items={[{ label: 'People', href: '/people' }, { label: p.name }]} />
        <header className="mb-6 flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-3.5">
            <Avatar name={p.name} size={40} />
            <div>
              <h1 className="text-[24px] leading-7 font-semibold tracking-[-0.02em]">{p.name}</h1>
              <p className="text-[14px] text-ink-2">
                {p.title} · {p.team}
                {p.manager ? ` · Reports to ${p.manager}` : ''}
              </p>
            </div>
          </div>
          {p.status === 'active' && people && row && !row.handover_id && <StartHandover person={p} people={people} />}
          {row?.handover_id && (
            <Link to={`/handovers/${encodeURIComponent(row.handover_id)}`}>
              <Button variant="secondary">Open handover</Button>
            </Link>
          )}
        </header>
        </>
      )}

      <Numbers p={p} self={you} />

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <Card>
            <CardHeader title={you ? 'What you do' : `What ${name} does`} right={p.eod_total ? 'Share of reports' : undefined} />
            {p.responsibilities.length === 0 ? (
              <Empty>Nothing recorded yet.</Empty>
            ) : (
              <ul>
                {p.responsibilities.map((r) => (
                  <li key={r.id} className="grid grid-cols-[minmax(0,1fr)_140px] items-center gap-6 border-b border-line py-2 last:border-0.5">
                    <div className="min-w-0">
                      <div className="truncate text-[14px] leading-5 font-medium">{r.title}</div>
                      <div className="truncate text-[13px] text-ink-3">
                        {[
                          r.cadence && CADENCE[r.cadence],
                          r.co_owners.length ? `With ${r.co_owners.join(', ')}` : r.via === 'transfer' ? 'Inherited' : only,
                        ]
                          .filter(Boolean)
                          .join(' · ')}
                        {r.overdue && ['monthly', 'quarterly'].includes(r.cadence ?? '') && <span className="text-risk-text"> · Overdue</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {r.share > 0 ? (
                        <>
                          <Bar value={r.share} max={1} risk={r.co_owners.length === 0} />
                          <span className="num w-8 shrink-0 text-right text-[13px] text-ink-2">{pct(r.share)}</span>
                        </>
                      ) : (
                        <span className="num w-full text-right text-[13px] text-ink-3">{plural(r.evidence, 'record')}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title={you ? 'What you know' : `What ${name} knows`} right={you ? 'You choose what is shared' : undefined} />
            {knowledge.length === 0 ? <Empty>Nothing recorded yet.</Empty> : (
              <ul>
                {knowledge.map((k) => (
                  <KnowledgeRow key={k.id} k={k} personId={p.id} onChange={reload} self={you} />
                ))}
              </ul>
            )}
          </Card>
        </div>

        <aside className="flex flex-col gap-4">
          <Card>
            <CardHeader title="Access" />
            {p.accounts.length === 0 ? <Empty>None recorded.</Empty> : (
              <ul>
                {p.accounts.map((a) => (
                  <li key={a.id} className="flex items-center gap-3 border-b border-line py-2 last:border-0">
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[14px]">{a.name}</div>
                      <div className="text-[13px] text-ink-3 capitalize">{a.role}</div>
                    </div>
                    {['admin', 'owner'].includes(a.role) && a.other_admins.length === 0 && <Chip tone="risk">Only admin</Chip>}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Relationships" />
            {p.stakeholders.length === 0 ? <Empty>None recorded.</Empty> : (
              <ul>
                {p.stakeholders.map((s) => (
                  <li key={s.id} className="border-b border-line py-2 last:border-0">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-[14px]">{s.name}</span>
                      {s.other_contacts.length === 0 && <Chip tone="risk">Only contact</Chip>}
                    </div>
                    <div className="text-[13px] text-ink-3">{[s.org, s.context].filter(Boolean).join(' · ')}</div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Skills" right="Records" />
            <ul>
              {p.skills.slice(0, 10).map((s) => (
                <li key={s.id} className="flex items-baseline justify-between py-1 text-[14px]">
                  <span className="text-ink-2">{s.name}</span>
                  <span className="num text-ink-3">{s.evidence}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <CardHeader title="Latest records" />
            <ul>
              {p.recent.slice(0, 6).map((s) => (
                <li key={s.id} className="flex items-baseline gap-3 border-b border-line py-2 last:border-0 text-[13px]">
                  <span className="min-w-0 flex-1 truncate text-ink-2">{s.sensitivity === 'personal' ? 'Personal note' : s.title}</span>
                  <span className="num shrink-0 text-ink-3">{date(s.at, true)}</span>
                </li>
              ))}
            </ul>
          </Card>
        </aside>
      </div>
    </>
  )
}
