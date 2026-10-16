import { Link } from 'react-router'
import { ShieldWarning, UserMinus, UsersThree } from '../../components/icons'
import { BackupsCard } from '../../components/Backups'
import { RampPlan } from '../../components/RampPlan'
import type { Me } from '../../hooks/useViewAs'
import { StatBand } from '../../components/StatBand'
import { Avatar, Bar, Card, CardHeader, Chip, PageHeader } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { date, first } from '../../lib/format'
import type { PersonRow } from '../../types/api'

/** A manager's home: their team's risk and the approvals waiting for them. */
export function ManagerHome({ me }: { me: Me }) {
  const { data: people, reload } = useApi<PersonRow[]>('/people') // the API returns only my team and me
  const team = (people ?? []).filter((p) => me.reports.includes(p.id))
  const open = me.managing.filter((h) => h.status !== 'transferred')
  const soleHeld = team.reduce((n, p) => n + p.risk, 0)
  const atRisk = team.filter((p) => p.risk > 0).length
  const maxRisk = Math.max(1, ...team.map((p) => p.risk))

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={`Your team, ${first(me.name)}`} sub={`${me.team ?? ''} · ${team.length} direct reports`} />

      <StatBand
        figures={[
          {
            label: 'Leaving from your team',
            value: open.length,
            note: open.map((h) => first(h.employee)).join(', ') || 'Nobody',
            tone: open.length ? 'text-risk-text' : undefined,
            icon: UserMinus,
          },
          { label: 'Held by one person', value: soleHeld, note: 'Work, accounts, contacts, knowledge', tone: soleHeld ? 'text-risk-text' : undefined, icon: ShieldWarning },
          {
            label: 'Teammates with sole items',
            value: `${atRisk}/${team.length}`,
            note: 'Hold something no one else does',
            icon: UsersThree,
            tone: atRisk ? 'text-soon' : 'text-ok-text',
            meter: team.length ? { value: atRisk, max: team.length } : undefined,
          },
        ]}
      />

      <Card>
        <CardHeader title="Needs your approval" meta={open.length} />
        {open.length === 0 ? (
          <p className="text-ink-3">Nothing waiting.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {open.map((h) => (
              <li key={h.id} className="flex items-center justify-between gap-4 py-2.5">
                <span className="flex items-center gap-2.5">
                  <Avatar name={h.employee} />
                  <span>
                    <span className="font-medium">{h.employee}</span>
                    <span className="text-ink-3"> → {h.successor ?? 'no successor yet'} · last day {date(h.effective_at, true)}</span>
                  </span>
                </span>
                <Link to={`/handovers/${encodeURIComponent(h.id)}?tab=transfer`} className="text-accent">
                  Review transfer
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {open
        .filter((h) => h.successor_id)
        .map((h) => (
          <RampPlan key={h.id} hid={h.id} mode="manager" successor={first(h.successor ?? '')} />
        ))}

      <BackupsCard team={team} me={me} onChange={reload} />

      <Card>
        <CardHeader title="What only one person holds" meta={team.length} />
        <ul className="flex flex-col gap-2.5">
          {[...team]
            .sort((a, b) => b.risk - a.risk)
            .map((p) => (
              <li key={p.id} className="grid grid-cols-[200px_1fr_auto] items-center gap-4">
                <Link to={`/people/${encodeURIComponent(p.id)}`} className="truncate hover:text-accent">
                  {p.name}
                </Link>
                <Bar value={p.risk} max={maxRisk} risk={p.risk > 0} />
                <span className="flex items-center gap-2">
                  <span className="num w-6 text-right text-ink-2">{p.risk}</span>
                  {p.handover_id && <Chip tone="risk">Leaving</Chip>}
                </span>
              </li>
            ))}
        </ul>
      </Card>
    </div>
  )
}
