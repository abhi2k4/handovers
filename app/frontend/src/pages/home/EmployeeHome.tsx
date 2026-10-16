import { Link } from 'react-router'
import { Database, Lifebuoy, Lock, ShieldWarning } from '../../components/icons'
import type { Me } from '../../hooks/useViewAs'
import { StatBand } from '../../components/StatBand'
import { Bar, Card, CardHeader, Chip, ErrorNote, PageHeader, PageSkeleton } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { first } from '../../lib/format'
import type { Person } from '../../types/api'

/** Everyone else's home: what the system knows about my work, and what only I hold. */
export function EmployeeHome({ me }: { me: Me }) {
  const { data: p, error, loading } = useApi<Person>(`/people/${encodeURIComponent(me.id)}`)
  if (loading && !p) return <PageSkeleton />
  if (error) return <ErrorNote message={error} />
  if (!p) return null

  const soloWork = p.responsibilities.filter((r) => r.co_owners.length === 0)
  const soloAccounts = p.accounts.filter((a) => a.other_admins.length === 0)
  const soloContacts = p.stakeholders.filter((s) => s.other_contacts.length === 0)
  const soloKnowledge = p.knowledge.filter((k) => k.others.length === 0)
  const onlyMe = soloWork.length + soloAccounts.length + soloContacts.length + soloKnowledge.length
  const backup = p.responsibilities.length ? Math.round((100 * (p.responsibilities.length - soloWork.length)) / p.responsibilities.length) : null
  const privateCount = p.knowledge.filter((k) => k.private).length
  const memory = '/me'

  const rows: { label: string; n: number; total: number }[] = [
    { label: 'Work', n: soloWork.length, total: p.responsibilities.length },
    { label: 'Accounts', n: soloAccounts.length, total: p.accounts.length },
    { label: 'Contacts', n: soloContacts.length, total: p.stakeholders.length },
    { label: 'Knowledge', n: soloKnowledge.length, total: p.knowledge.length },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={`Hi ${first(me.name)}`} sub={`${p.title} · ${p.team}${p.manager ? ` · reports to ${p.manager}` : ''}`} />

      <StatBand
        figures={[
          { label: 'Only you hold', value: onlyMe, note: 'Work, accounts, contacts, knowledge', tone: onlyMe ? 'text-soon' : undefined, icon: ShieldWarning },
          {
            label: 'Your work with a backup',
            value: backup === null ? '–' : `${backup}%`,
            note: `${p.responsibilities.length - soloWork.length} of ${p.responsibilities.length}`,
            tone: backup !== null && backup < 50 ? 'text-risk-text' : undefined,
            icon: Lifebuoy,
            meter: backup !== null ? { value: backup, max: 100, target: 80 } : undefined,
          },
          { label: 'Work records', value: p.sources, note: 'Learned from your tools', icon: Database },
          { label: 'Kept private', value: privateCount, note: `of ${p.knowledge.length} items`, href: memory, icon: Lock },
        ]}
      />

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="What only you hold" meta={onlyMe} right={<Link to={memory} className="text-accent">Open my memory</Link>} />
          <ul className="flex flex-col gap-2.5">
            {rows.map((r) => (
              <li key={r.label} className="grid grid-cols-[90px_1fr_auto] items-center gap-4">
                <span>{r.label}</span>
                <Bar value={r.n} max={Math.max(1, r.total)} risk={r.n > 0} />
                <span className="num w-14 text-right text-ink-2">
                  {r.n}/{r.total}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardHeader title="Your responsibilities" meta={p.responsibilities.length} />
          <ul className="flex flex-col divide-y divide-line">
            {p.responsibilities.slice(0, 6).map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-4 py-2">
                <span className="min-w-0 truncate">{r.title}</span>
                {r.co_owners.length === 0 ? <Chip tone="soon">Only you</Chip> : <Chip tone="ok">Shared</Chip>}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <p className="text-[13px] text-ink-3">
        Learned from your work. Correct anything or keep it private in{' '}
        <Link to={memory} className="text-accent">
          your memory
        </Link>
        .
      </p>
    </div>
  )
}
