import { ChevronRight, ShieldWarning, UserMinus } from '../../components/icons'
import { useState } from 'react'
import { Link } from 'react-router'
import { HBars, StackBar } from '../../components/charts'
import { Legend, Readiness, SimulationSheet } from '../../components/OrgRisk'
import { StatBand } from '../../components/StatBand'
import { Avatar, Card, CardHeader, Chip, ErrorNote, PageHeader, PageSkeleton } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import type { Me } from '../../hooks/useViewAs'
import { date, first } from '../../lib/format'
import { figure, type Kpis } from '../../lib/kpis'
import { type DashHandover, health, KINDS, type RiskPerson } from '../../lib/orgRisk'

/** Not ready and short on time, an account only the leaver can open, or no successor. */
function atRisk(h: DashHandover): boolean {
  const st = health(h).tone
  return st === 'risk' || st === 'soon'
}

/** Leadership: how much the company holds in one head, where, and whether handovers land. Read-only. */
export function LeadershipHome({ me }: { me: Me }) {
  const { data: k, error, loading } = useApi<Kpis>('/kpis')
  const [picked, setPicked] = useState<RiskPerson | null>(null)
  if (loading && !k) return <PageSkeleton />
  if (error || !k) return <ErrorNote message={error ?? 'Failed to load'} />

  const kpi = (key: string) => [...k.risk, ...k.process, ...k.outcomes].find((x) => x.key === key)
  const coverage = kpi('backup_coverage')
  const north = kpi('north_star')
  const risky = k.handovers.filter(atRisk)
  const soonest = [...k.handovers].sort((a, b) => a.days_left - b.days_left)[0]
  const teams = k.teams.filter((t) => t.total > 0).sort((a, b) => (a.coverage ?? 0) - (b.coverage ?? 0))
  const people = k.people.slice(0, 6)
  const maxRisk = Math.max(1, ...people.map((p) => p.risk))
  const approvals = me.managing.filter((h) => h.status !== 'transferred')
  // A leaver outside the top list still opens the panel; its counts come from the simulation.
  const pick = (h: DashHandover) =>
    setPicked(k.people.find((p) => p.id === h.employee_id) ?? { id: h.employee_id, name: h.employee, title: h.title, team: '', risk: 0, sole: {}, leaving: true })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Leadership" sub={`${k.company} · ${date(k.now)} · ${k.headcount.active} active, ${k.headcount.leaving} leaving`} />

      <StatBand
        figures={[
          { label: 'Held by one person', value: kpi('held_by_one')?.value ?? 0, note: 'Work, accounts, contacts, knowledge', tone: 'text-risk-text', icon: ShieldWarning },
          ...(coverage ? [figure(coverage)] : []),
          {
            label: 'Handovers at risk',
            value: `${risky.length}/${k.handovers.length}`,
            note: soonest ? `${first(soonest.employee)}, ${soonest.days_left} days left` : 'Nobody leaving',
            tone: risky.length ? 'text-risk-text' : undefined,
            icon: UserMinus,
            meter: k.handovers.length ? { value: risky.length, max: k.handovers.length } : undefined,
          },
          ...(north ? [figure(north)] : []),
        ]}
      />

      {approvals.length > 0 && (
        <Card>
          <CardHeader title="Needs your approval" meta={approvals.length} />
          <ul className="-mx-2 flex flex-col">
            {approvals.map((h) => (
              <li key={h.id}>
                <Link to={`/handovers/${encodeURIComponent(h.id)}?tab=transfer`} className="flex items-center justify-between gap-3 rounded-[4px] px-2 py-2.5 hover:bg-app">
                  <span className="flex min-w-0 items-center gap-3">
                    <Avatar name={h.employee} size={28} />
                    <span className="truncate text-[15px] font-medium">
                      {h.employee} → {h.successor ?? 'no successor yet'}
                    </span>
                  </span>
                  <span className="text-[13px] font-medium text-accent">Review</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid items-start gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Work with a backup, by team" />
          <HBars
            unit="%"
            max={100}
            target={80}
            labelWidth={110}
            rows={teams.map((t) => {
              const c = t.coverage ?? 0
              return { key: t.id, label: t.name, value: c, sub: `${t.sole}/${t.total} solo`, tone: c < 50 ? 'risk' : c < 80 ? 'soon' : 'ok' }
            })}
          />
        </Card>

        <Card>
          <CardHeader title="Single points of failure" right={<Legend />} />
          <ul className="-mx-2 flex flex-col">
            {people.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => setPicked(p)}
                  className="grid h-11 w-full grid-cols-[minmax(0,150px)_minmax(0,1fr)_32px] items-center gap-4 rounded-[4px] px-2 text-left transition-colors hover:bg-app"
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    <Avatar name={p.name} size={26} />
                    <span className="min-w-0">
                      <span className="block truncate text-[14px] font-medium">{p.name}</span>
                      <span className="block truncate text-[12px] text-ink-3">{p.team}</span>
                    </span>
                  </span>
                  <span className="flex items-center gap-3">
                    <span className="flex-1">
                      <StackBar height={10} max={maxRisk} parts={KINDS.map((x) => ({ label: x.label, value: p.sole[x.key] ?? 0, color: x.color }))} />
                    </span>
                    {p.leaving && <Chip tone="risk">Leaving</Chip>}
                  </span>
                  <span className="num text-right text-[15px] font-semibold">{p.risk}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <CardHeader title="Handovers in flight" meta={k.handovers.length || undefined} />
        {k.handovers.length === 0 ? (
          <p className="text-[14px] text-ink-3">Nobody is leaving.</p>
        ) : (
          <ul className="-mx-2 flex flex-col">
            {[...k.handovers]
              .sort((a, b) => a.days_left - b.days_left)
              .map((h) => {
                const st = health(h)
                return (
                  <li key={h.id}>
                    <button
                      onClick={() => pick(h)}
                      className="grid w-full items-center gap-x-5 gap-y-2 rounded-[4px] px-2 py-2.5 text-left transition-colors hover:bg-app sm:grid-cols-[minmax(0,1fr)_auto_auto_auto]"
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <Avatar name={h.employee} size={32} />
                        <span className="min-w-0">
                          <span className="block truncate text-[15px] font-medium">{h.employee}</span>
                          <span className={`block truncate text-[13px] ${h.successor ? 'text-ink-3' : 'text-soon'}`}>{h.successor ? `To ${h.successor}` : 'No successor yet'}</span>
                        </span>
                      </span>
                      <Readiness h={h} />
                      <span className={`num text-[14px] ${h.days_left <= 7 ? 'font-medium text-risk-text' : 'text-ink-2'}`}>{h.days_left} days left</span>
                      <span className="flex items-center gap-2">
                        <Chip tone={st.tone}>{st.label}</Chip>
                        <ChevronRight size={16} strokeWidth={1.75} className="text-ink-3 max-sm:hidden" />
                      </span>
                    </button>
                  </li>
                )
              })}
          </ul>
        )}
      </Card>

      <section>
        <h2 className="mb-3 text-[14px] font-medium text-ink-2">Outcomes of completed handovers</h2>
        <StatBand figures={k.outcomes.map(figure)} />
      </section>

      {picked && <SimulationSheet person={picked} actions={false} onClose={() => setPicked(null)} />}
    </div>
  )
}
