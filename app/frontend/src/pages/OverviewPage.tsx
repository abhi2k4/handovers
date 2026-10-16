import { ChatCircleDots, ChevronRight, Lifebuoy, Plus, ShieldWarning, UserMinus, UserPlus } from '../components/icons'
import { useState } from 'react'
import { Link } from 'react-router'
import { Breakdown, HBars, StackBar, StepBars } from '../components/charts'
import { Legend, SimulationSheet } from '../components/OrgRisk'
import { StageChip } from '../components/Pipeline'
import { StartExit } from '../components/StartExit'
import { type DashHandover, health, type Kind, KINDS, type RiskPerson } from '../lib/orgRisk'
import { type Figure, StatBand } from '../components/StatBand'
import { Avatar, Button, Card, CardHeader, Chip, ErrorNote, PageSkeleton } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { first } from '../lib/format'

interface Attention {
  severity: 'bad' | 'warn' | 'info'
  kind: 'access' | 'successor' | 'interview' | 'transfer' | 'overdue' | 'review' | 'candidate'
  title: string
  detail: string
  href: string
}

interface Dashboard {
  now: number
  company: string
  headcount: { active: number; leaving: number; joining: number; departed: number }
  attention: Attention[]
  handovers: DashHandover[]
  risk: {
    total: number
    by_kind: Record<Kind, number>
    people: RiskPerson[]
    teams: { id: string; name: string; total: number; sole: number }[]
  }
  health: Record<'unexplained' | 'contradictions' | 'procedures' | 'undocumented', { count: number; example: string | null }>
  activity: { start: number; days: Record<string, number>; total: number; review: number }
  joiners: { id: string; name: string; title: string; starts: number; inherits_from: string | null }[]
}

/* ---------------------------------------------------------------- summary */

/** One band, four numbers, no boxes. "Held by one person" leads: it is what this product is about. */
function Summary({ d }: { d: Dashboard }) {
  const open = d.handovers.filter((h) => h.status !== 'transferred')
  const soonest = [...open].sort((a, b) => a.days_left - b.days_left)[0]
  const teams = d.risk.teams.filter((t) => t.total > 0)
  const total = teams.reduce((n, t) => n + t.total, 0)
  const covered = teams.reduce((n, t) => n + t.total - t.sole, 0)
  const coverage = total ? Math.round((covered / total) * 100) : 0
  const questions = open.reduce((n, h) => n + h.questions, 0)
  const answered = open.reduce((n, h) => n + h.answered, 0)

  const figures: Figure[] = [
    { label: 'Held by one person', value: d.risk.total, note: 'Work, accounts, contacts, knowledge', icon: ShieldWarning, tone: d.risk.total ? 'text-risk-text' : undefined },
    {
      label: 'Work with a backup',
      value: `${coverage}%`,
      note: `${covered} of ${total} responsibilities, target 80%`,
      tone: coverage < 25 ? 'text-risk-text' : coverage < 50 ? 'text-soon' : coverage >= 80 ? 'text-ok-text' : undefined,
      icon: Lifebuoy,
      meter: { value: coverage, max: 100, target: 80 },
    },
    {
      label: 'Leaving',
      value: open.length,
      note: soonest ? `${first(soonest.employee)}, ${soonest.days_left} days left` : 'Nobody',
      href: soonest ? `/handovers/${encodeURIComponent(soonest.id)}` : undefined,
      icon: UserMinus,
    },
    {
      label: 'Exit answers',
      value: questions ? `${answered}/${questions}` : '–',
      note: questions ? `${Math.round((answered / questions) * 100)}% captured so far` : 'None open',
      icon: ChatCircleDots,
      meter: questions ? { value: answered, max: questions } : undefined,
    },
  ]

  return <StatBand figures={figures} />
}

/* ---------------------------------------------------------------- handovers */

function Handovers({ handovers, onStart }: { handovers: DashHandover[]; onStart: () => void }) {
  const open = handovers.filter((h) => h.status !== 'transferred')
  return (
    <Card>
      <CardHeader
        title="Handovers"
        meta={open.length || undefined}
        right={
          <Link to="/handovers" className="hover:text-ink">
            View all
          </Link>
        }
      />
      {open.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <UserPlus size={18} strokeWidth={1.75} className="text-ink-3" />
          <div className="text-[15px] font-medium">No one is leaving</div>
          <Button variant="secondary" onClick={onStart}>
            <Plus size={14} strokeWidth={2} /> Start handover
          </Button>
        </div>
      ) : (
        <>
          <div className="mb-4">
            <StepBars steps={stageCounts(open)} />
          </div>
          <ul className="-mx-2 flex flex-col border-t border-line pt-2">
          {open.map((h) => {
            const st = health(h)
            return (
              <li key={h.id}>
                <Link
                  to={`/handovers/${encodeURIComponent(h.id)}`}
                  className="grid items-center gap-x-5 gap-y-2 rounded-[4px] px-2 py-2.5 transition-colors hover:bg-app sm:grid-cols-[minmax(0,1fr)_auto_auto]"
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <Avatar name={h.employee} size={32} />
                    <span className="min-w-0">
                      <span className="block truncate text-[15px] font-medium">{h.employee}</span>
                      <span className={`block truncate text-[13px] ${h.successor ? 'text-ink-3' : 'text-soon'}`}>
                        {h.successor ? `To ${h.successor}` : 'No successor yet'}
                      </span>
                    </span>
                  </span>
                  <span className={`num text-[14px] ${h.days_left <= 7 ? 'font-medium text-risk-text' : 'text-ink-2'}`}>{h.days_left} days left</span>
                  <span className="flex items-center gap-2">
                    <StageChip stages={h.stages} />
                    <Chip tone={st.tone}>{st.label}</Chip>
                    <ChevronRight size={16} strokeWidth={1.75} className="text-ink-3 max-sm:hidden" />
                  </span>
                </Link>
              </li>
            )
          })}
          </ul>
        </>
      )}
    </Card>
  )
}

/** Open handovers per exit stage, in pipeline order. */
function stageCounts(open: DashHandover[]) {
  const current = (h: DashHandover) => (h.stages.find((x) => x.state === 'current') ?? h.stages[h.stages.length - 1])?.key
  return (open[0]?.stages ?? []).map((s) => ({ key: s.key, label: s.label, value: open.filter((h) => current(h) === s.key).length }))
}

/* ---------------------------------------------------------------- attention */

const ACTION: Record<Attention['kind'], string> = {
  access: 'Reassign',
  successor: 'Choose',
  interview: 'Open',
  transfer: 'Approve',
  overdue: 'View',
  review: 'Review',
  candidate: 'Review',
}

const SEVERITY_DOT = { bad: 'bg-risk', warn: 'bg-soon-fill', info: 'bg-accent-fill' }

function NeedsAttention({ items }: { items: Attention[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? items : items.slice(0, 5)
  return (
    <Card>
      <CardHeader
        title="Needs attention"
        meta={items.length || undefined}
        right={
          items.length > 5 && (
            <button onClick={() => setAll((a) => !a)} className="hover:text-ink">
              {all ? 'Fewer' : 'View all'}
            </button>
          )
        }
      />
      {items.length === 0 ? (
        <p className="text-[14px] text-ink-2">All clear.</p>
      ) : (
        <ul className="-mx-2 flex flex-col">
          {shown.map((i, n) => (
            <li key={`${i.kind}-${n}`}>
              <Link to={i.href} className="grid grid-cols-[8px_minmax(0,1fr)_auto] items-center gap-3 rounded-[4px] px-2 py-2 transition-colors hover:bg-app">
                <span className={`size-2 rounded-full ${SEVERITY_DOT[i.severity]}`} aria-hidden />
                <span className="min-w-0">
                  <span className="block truncate text-[14px] font-medium">{i.title}</span>
                  <span className="block truncate text-[13px] text-ink-3">{i.detail}</span>
                </span>
                <span className="text-[13px] font-medium text-accent">{ACTION[i.kind] ?? 'Open'}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

/* ---------------------------------------------------------------- risk */

function SoleHolders({ people, onPick }: { people: RiskPerson[]; onPick: (p: RiskPerson) => void }) {
  const max = Math.max(1, ...people.map((p) => p.risk))
  return (
    <Card>
      <CardHeader title="Who holds what no one else does" right={<Legend />} />
      <ul className="-mx-2 flex flex-col">
        {people.slice(0, 7).map((p) => (
          <li key={p.id}>
            <button
              onClick={() => onPick(p)}
              className="grid h-11 w-full grid-cols-[minmax(0,170px)_minmax(0,1fr)_36px] items-center gap-4 rounded-[4px] px-2 text-left transition-colors duration-150 hover:bg-app"
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
                  <StackBar
                    height={10}
                    max={max}
                    parts={KINDS.map((k) => ({ label: k.label, value: p.sole[k.key] ?? 0, color: k.color }))}
                  />
                </span>
                {p.leaving && <Chip tone="risk">Leaving</Chip>}
              </span>
              <span className="num text-right text-[15px] font-semibold">{p.risk}</span>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  )
}

/* ---------------------------------------------------------------- page */

const weekday = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })

/** HR and leadership: where the company is about to lose knowledge, and what to do today. Trends live on Insights. */
export function OverviewPage() {
  const { data: d, error, loading } = useApi<Dashboard>('/dashboard')
  const [picked, setPicked] = useState<RiskPerson | null>(null)
  const [starting, setStarting] = useState(false)
  if (loading && !d) return <PageSkeleton />
  if (error || !d) return <ErrorNote message={error ?? 'Failed to load'} />

  return (
    <div className="flex flex-col gap-4">
      <header className="mb-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] leading-8 font-semibold tracking-[-0.02em]">Overview</h1>
          <p className="mt-0.5 text-[14px] text-ink-3">{weekday.format(new Date(d.now))}</p>
        </div>
        <Button onClick={() => setStarting(true)}>
          <Plus size={14} strokeWidth={2} /> Start handover
        </Button>
      </header>

      <Summary d={d} />

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Handovers handovers={d.handovers} onStart={() => setStarting(true)} />
        <NeedsAttention items={d.attention} />
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <SoleHolders people={d.risk.people} onPick={setPicked} />
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader title="Held by one person, by kind" />
            <Breakdown caption="items" parts={KINDS.map((k) => ({ label: k.label, value: d.risk.by_kind[k.key] ?? 0, color: k.color }))} />
          </Card>
          <Card>
            <CardHeader title="Work with a backup, by team" />
            <HBars
              unit="%"
              max={100}
              target={80}
              labelWidth={104}
              rows={d.risk.teams
                .filter((t) => t.total > 0)
                .map((t) => ({ t, c: Math.round(((t.total - t.sole) / t.total) * 100) }))
                .sort((a, b) => a.c - b.c)
                .map(({ t, c }) => ({ key: t.id, label: t.name, value: c, tone: c < 50 ? 'risk' : c < 80 ? 'soon' : 'ok' }))}
            />
          </Card>
        </div>
      </div>

      {picked && <SimulationSheet person={picked} onClose={() => setPicked(null)} />}
      {starting && <StartExit now={d.now} onClose={() => setStarting(false)} />}
    </div>
  )
}
