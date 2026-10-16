import { Link } from 'react-router'
import { Breakdown, Gauge, HBars, StackBar } from '../components/charts'
import { Legend } from '../components/OrgRisk'
import { Avatar, Bar, Card, CardHeader, Chip, ErrorNote, PageHeader, PageSkeleton } from '../components/ui'
import { StatBand } from '../components/StatBand'
import { TrendCards } from '../components/TrendCards'
import { useApi } from '../hooks/useApi'
import { date } from '../lib/format'
import { figure, type Kpis, show, tone } from '../lib/kpis'
import { KINDS } from '../lib/orgRisk'

function Heading({ children }: { children: string }) {
  return <h2 className="mt-2 text-[14px] font-semibold text-ink-2">{children}</h2>
}

/** One handover's progress: answers, accounts and gaps as three small meters. */
function Progress({ label, done, total, risk = false }: { label: string; done: number; total: number; risk?: boolean }) {
  return (
    <div className="min-w-0">
      <div className="mb-1 flex items-baseline justify-between gap-2 text-[12px]">
        <span className="truncate text-ink-3">{label}</span>
        <span className="num font-medium text-ink-2">
          {done}/{total}
        </span>
      </div>
      <Bar value={done} max={Math.max(1, total)} tone={total === 0 || done === total ? 'ok' : risk ? 'risk' : 'accent'} />
    </div>
  )
}

export function InsightsPage() {
  const { data: k, error, loading } = useApi<Kpis>('/kpis')
  if (loading && !k) return <PageSkeleton />
  if (error) return <ErrorNote message={error} />
  if (!k) return null

  const north = k.process.find((p) => p.key === 'north_star')
  const process = k.process.filter((p) => p.key !== 'north_star')
  const northTone = north ? tone(north) : undefined
  const maxRisk = Math.max(1, ...k.people.map((x) => x.risk))

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Insights" sub={`${k.company} · ${date(k.now)} · ${k.headcount.active} active, ${k.headcount.leaving} leaving, ${k.headcount.joining} joining`} />

      {north && (
        <Card>
          <div className="flex flex-wrap items-center gap-x-10 gap-y-6">
            <Gauge value={north.value} tone={northTone === 'ok' ? 'ok' : northTone === 'soon' ? 'soon' : 'risk'} size={148} thickness={14} label={`target ${north.target}%`} />
            <div className="min-w-0 flex-1">
              <div className="text-[13px] font-medium text-accent">North star</div>
              <div className="mt-1 text-[22px] leading-7 font-semibold tracking-[-0.01em]">{north.label}</div>
              <p className="mt-1.5 max-w-xl text-[14px] text-ink-2">{north.detail}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {north.value === null ? (
                  <Chip>No handover has reached its last day yet</Chip>
                ) : (
                  <Chip tone={northTone === 'ok' ? 'ok' : 'risk'}>{northTone === 'ok' ? 'On target' : `${show(north)} of ${north.target}% target`}</Chip>
                )}
                <Chip>{k.handovers.length} handovers in progress</Chip>
              </div>
            </div>
            <div className="grid w-full grid-cols-3 gap-2 sm:w-auto sm:grid-cols-1">
              {(
                [
                  ['Active', k.headcount.active],
                  ['Leaving', k.headcount.leaving],
                  ['Joining', k.headcount.joining],
                ] as const
              ).map(([label, n]) => (
                <div key={label} className="flex items-baseline justify-between gap-6 rounded-[4px] bg-app px-3 py-2">
                  <span className="text-[13px] text-ink-3">{label}</span>
                  <span className="num text-[16px] font-semibold">{n}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      <Heading>Handover process</Heading>
      <StatBand figures={process.map(figure)} />

      <Heading>Key-person risk and knowledge health</Heading>
      <StatBand figures={k.risk.map(figure)} />

      <div className="grid items-start gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Work with a backup, by team" meta="2+ holders" />
          <HBars
            unit="%"
            max={100}
            target={80}
            rows={[...k.teams]
              .filter((t) => t.total > 0)
              .sort((a, b) => (a.coverage ?? 0) - (b.coverage ?? 0))
              .map((t) => {
                const c = t.coverage ?? 0
                return { key: t.id, label: t.name, value: c, sub: `${t.sole}/${t.total} solo`, tone: c < 50 ? 'risk' : c < 80 ? 'soon' : 'ok' }
              })}
          />
        </Card>

        <Card>
          <CardHeader title="What one person holds, by kind" />
          <Breakdown caption="held by one" parts={KINDS.map((x) => ({ label: x.label, value: k.risk_by_kind[x.key] ?? 0, color: x.color }))} />
        </Card>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Handovers in progress" meta={k.handovers.length} />
          {k.handovers.length === 0 ? (
            <p className="text-ink-3">None.</p>
          ) : (
            <ul className="-mx-2 flex flex-col">
              {k.handovers.map((h) => (
                <li key={h.id}>
                  <Link to={`/handovers/${encodeURIComponent(h.id)}`} className="flex flex-col gap-3 rounded-[4px] px-2 py-3 transition-colors hover:bg-app">
                    <span className="flex items-center justify-between gap-3">
                      <span className="flex min-w-0 items-center gap-2.5">
                        <Avatar name={h.employee} size={28} />
                        <span className="truncate text-[14px] font-medium">
                          {h.employee} <span className="font-normal text-ink-3">to {h.successor ?? 'no successor yet'}</span>
                        </span>
                      </span>
                      <Chip tone={h.days_left < 7 ? 'risk' : 'soon'}>{h.days_left} days left</Chip>
                    </span>
                    <span className="grid grid-cols-3 gap-4 pl-[38px]">
                      <Progress label="Exit answers" done={h.answered} total={h.questions} />
                      <span className="min-w-0">
                        <span className="mb-1 block truncate text-[12px] text-ink-3">Sole-admin accounts</span>
                        <span className={`flex items-center gap-1.5 text-[13px] font-medium ${h.open_access ? 'text-risk-text' : 'text-ok-text'}`}>
                          <span className={`size-2 rounded-full ${h.open_access ? 'bg-risk' : 'bg-ok'}`} aria-hidden />
                          {h.open_access ? `${h.open_access} still open` : 'All handled'}
                        </span>
                      </span>
                      <Progress label="Gaps closed" done={h.gaps - h.open_gaps} total={h.gaps} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader title="Most held by one person" />
          <div className="-mt-2 mb-3 text-[13px] text-ink-3">
            <Legend />
          </div>
          <ul className="-mx-2 flex flex-col">
            {k.people.map((p) => (
              <li key={p.id}>
                <Link
                  to={`/people/${encodeURIComponent(p.id)}`}
                  className="grid h-10 grid-cols-[minmax(0,140px)_minmax(0,1fr)_auto] items-center gap-4 rounded-[4px] px-2 transition-colors hover:bg-app"
                >
                  <span className="truncate text-[14px]">{p.name}</span>
                  <StackBar height={10} max={maxRisk} parts={KINDS.map((x) => ({ label: x.label, value: p.sole[x.key] ?? 0, color: x.color }))} />
                  <span className="flex items-center justify-end gap-2">
                    {p.leaving && <Chip tone="risk">Leaving</Chip>}
                    <span className="num w-6 text-right text-[14px] font-semibold">{p.risk}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <TrendCards />

      <Heading>Outcomes of completed handovers</Heading>
      <StatBand figures={k.outcomes.map(figure)} />
    </div>
  )
}
