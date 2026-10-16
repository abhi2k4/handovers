import { Check } from '../../components/icons'
import { useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useViewAs } from '../../hooks/useViewAs'
import { Avatar, Breadcrumb, ErrorNote, PageSkeleton, Segmented, Select } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { api } from '../../lib/api'
import { date, daysBetween, first } from '../../lib/format'
import type { Handover, PersonRow } from '../../types/api'
import { ExitInterview } from './ExitInterview'
import { InterviewKitView } from './InterviewKitView'
import { JobDescriptionView } from './JobDescriptionView'
import { Overview } from './Overview'
import { PlanView } from './PlanView'
import { ClearanceView } from './ClearanceView'
import { CandidatesView } from './CandidatesView'
import { RampPlan } from '../../components/RampPlan'
import { Pipeline, type Stage } from '../../components/Pipeline'
import { Screening } from './Screening'
import { CancelHandover } from './CancelHandover'
import { useConfirmable } from '../../components/Confirm'
import { successorOptions } from '../../lib/successors'
import { TransferView } from './TransferView'

export type Tab = 'overview' | 'jd' | 'candidates' | 'screening' | 'kit' | 'plan' | 'interview' | 'transfer' | 'ramp' | 'clearance'

const HIRING: { value: Tab; label: string }[] = [
  { value: 'jd', label: 'Job description' },
  { value: 'candidates', label: 'Candidates' },
  { value: 'screening', label: 'Screening' },
  { value: 'kit', label: 'Interview kit' },
]

interface Meta {
  now: number
}

/** HR sees exit-interview progress, never the answers (docs/product-strategy.md section 10.1). */
function InterviewProgress({ h }: { h: Handover }) {
  const qs = h.gaps.filter((g) => g.interview && g.status !== 'dismissed')
  const done = qs.filter((g) => g.status === 'answered').length
  return (
    <div className="flex flex-col gap-3">
      <p className="text-ink-2">
        {done} of {qs.length} answered. Only {h.employee} and {h.manager ?? 'their manager'} can read the answers.
      </p>
      <ul className="flex flex-col divide-y divide-line">
        {qs.map((g, i) => (
          <li key={g.id} className="flex items-center justify-between py-2">
            <span className="text-ink-2">
              Question {i + 1} · {g.label}
            </span>
            <span className={g.status === 'answered' ? 'text-ok-text' : 'text-ink-3'}>{g.status}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function HandoverPage() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as Tab) || 'overview'
  const { data: h, error, loading, reload } = useApi<Handover>(`/handovers/${encodeURIComponent(id)}`)
  const { data: people } = useApi<PersonRow[]>('/people')
  const { data: meta } = useApi<Meta>('/meta')
  const { data: readiness } = useApi<{ stages: Stage[] }>(`/handovers/${encodeURIComponent(id)}/readiness`)
  const { persona, me, has } = useViewAs()
  const content = useRef<HTMLDivElement>(null)
  const confirmable = useConfirmable()
  const [pickError, setPickError] = useState('')

  if (loading && !h) return <PageSkeleton />
  if (error || !h) return <ErrorNote message={error ?? 'Not found'} />

  // Per-role view: HR gets progress, not content; only HR and the manager run hiring.
  const redacted = (h as Handover & { redacted?: boolean }).redacted === true
  const runsHiring = !persona || has('hr') || (me?.reports.includes(h.employee_id) ?? false)
  const hidden = new Set<Tab>([...(redacted ? (['transfer'] as Tab[]) : []), ...(runsHiring ? [] : (['jd', 'candidates', 'screening', 'kit', 'plan', 'ramp'] as Tab[]))])

  // A history entry per step, so Back returns to the previous step. Keep the scroll, but bring the
  // step's content into view if the reader had scrolled past its top.
  const setTab = (t: Tab) => {
    if (t === tab) return
    setParams(t === 'overview' ? {} : { tab: t }, { preventScrollReset: true })
    const top = content.current ? content.current.getBoundingClientRect().top + window.scrollY - 96 : 0
    if (window.scrollY > top) window.scrollTo({ top, behavior: 'smooth' })
  }
  const now = meta?.now ?? h.created_at
  const daysLeft = daysBetween(now, h.effective_at)
  const done = h.status === 'transferred'
  const questions = h.gaps.filter((g) => g.interview && g.status !== 'dismissed')
  const answered = questions.filter((g) => g.status === 'answered').length

  const allSteps: { value: Tab; label: string; meta?: string; done?: boolean; group: string }[] = [
    { value: 'overview', label: 'Overview', group: '' },
    { value: 'interview', label: 'Exit interview', group: 'Hand over', meta: `${answered}/${questions.length}`, done: questions.length > 0 && answered === questions.length },
    { value: 'plan', label: 'Handover document', group: 'Hand over' },
    { value: 'transfer', label: 'Transfer', group: 'Hand over', done },
    { value: 'ramp', label: 'Ramp-up plan', group: 'Hand over' },
    { value: 'clearance', label: 'Clearance', group: 'Exit' },
    // One step for hiring: job description, screening and interview kit switch inside it.
    { value: 'jd', label: 'Hiring', group: 'Replace' },
  ]
  const steps = allSteps.filter((step) => !hidden.has(step.value))

  async function chooseSuccessor(successor: string) {
    if (!successor) return
    setPickError('')
    try {
      await confirmable.run((confirmed) => api.post(`/handovers/${encodeURIComponent(id)}/successor`, { successor_id: successor, confirmed }))
      reload()
    } catch (e) {
      setPickError(e instanceof Error ? e.message : 'Failed')
    }
  }
  const cancelled = h.status === 'cancelled'
  const candidates = successorOptions(people ?? [], { id: h.employee_id, team: h.team, team_id: h.team_id })

  let group = ''
  return (
    <>
      <Breadcrumb items={[{ label: 'Handovers', href: '/handovers' }, { label: h.employee }]} />
      <header className="mb-5 flex flex-wrap items-center justify-between gap-6">
        <div className="flex items-center gap-3.5">
          <Avatar name={h.employee} size={40} />
          <div>
            <h1 className="text-[24px] leading-7 font-semibold tracking-[-0.02em]">
              <Link to={`/people/${encodeURIComponent(h.employee_id)}`} className="hover:underline">
                {h.employee}
              </Link>
            </h1>
            <p className="text-[14px] text-ink-2">{h.title}</p>
          </div>
        </div>
        <dl className="flex gap-10 text-[14px]">
          {h.approver && h.status !== 'cancelled' && (
            <div>
              <dt className="text-[13px] text-ink-3">Approver</dt>
              <dd className="mt-0.5 font-medium" title={h.approver.via === 'manager' ? undefined : 'The manager is away or leaving, so approval moves up'}>
                {h.approver.name}
                {h.approver.via !== 'manager' && <span className="font-normal text-ink-3"> · {h.approver.via === 'hr' ? 'no manager' : 'skip-level'}</span>}
              </dd>
            </div>
          )}
          <div>
            <dt className="text-[13px] text-ink-3">Last day</dt>
            <dd className="mt-0.5">
              {cancelled ? (
                <span className="text-ink-3">Cancelled</span>
              ) : daysLeft === 0 ? (
                <span className="num font-medium">{h.employee_status === 'departed' ? 'Left' : 'Today'} · {date(h.effective_at, true)}</span>
              ) : (
                <>
                  <span className={`num font-medium ${daysLeft <= 7 ? 'text-risk-text' : ''}`}>In {daysLeft} days</span>
                  <span className="num text-ink-3"> · {date(h.effective_at, true)}</span>
                </>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-[13px] text-ink-3">Successor</dt>
            <dd className="mt-0.5">
              {h.successor ? (
                <Link to={`/people/${encodeURIComponent(h.successor_id ?? '')}`} className="font-medium hover:underline">
                  {h.successor}
                </Link>
              ) : cancelled || !h.can?.run ? (
                <span className="text-ink-3">Not chosen</span>
              ) : (
                <Select value="" onChange={(e) => void chooseSuccessor(e.target.value)} aria-label="Choose successor">
                  <option value="">Choose…</option>
                  {candidates.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                      {p.status === 'incoming' ? ' (joining)' : ''}
                      {p.sameTeam ? '' : ` · ${p.team}`}
                    </option>
                  ))}
                </Select>
              )}
              {pickError && <span className="mt-1 block max-w-[220px] text-[12px] text-risk-text">{pickError}</span>}
            </dd>
          </div>
        </dl>
      </header>
      {confirmable.dialog}
      {cancelled ? (
        <div className="mb-8 rounded-[6px] bg-app px-4 py-3 text-[14px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)]">
          <span className="font-medium text-ink">Cancelled</span>
          {h.cancelled_at ? ` on ${date(h.cancelled_at, true)}` : ''}. {h.cancel_reason}
        </div>
      ) : (
        <div className="mb-10 flex flex-wrap items-center justify-between gap-3">
          {readiness && <Pipeline stages={readiness.stages} />}
          <CancelHandover h={h} onDone={reload} />
        </div>
      )}

      <div className="grid gap-10 md:grid-cols-[176px_minmax(0,1fr)] xl:gap-14">
        <nav className="md:sticky md:top-[88px] md:self-start" aria-label="Handover steps">
          <ul className="flex gap-1 overflow-x-auto md:flex-col md:gap-px">
            {steps.map((s) => {
              const header = s.group && s.group !== group ? s.group : null
              group = s.group || group
              const active = tab === s.value || (s.value === 'jd' && HIRING.some((x) => x.value === tab))
              return (
                <li key={s.value}>
                  {header && <div className="eyebrow mt-5 mb-1.5 hidden px-2.5 md:block">{header}</div>}
                  <button
                    onClick={() => setTab(s.value)}
                    aria-current={active ? 'page' : undefined}
                    className={`flex h-9 w-full items-center gap-2 rounded-[4px] px-2.5 text-left text-[14px] whitespace-nowrap transition-colors duration-150 ${
                      active ? 'bg-page font-medium text-ink shadow-[inset_0_0_0_1px_var(--color-line)]' : 'text-ink-2 hover:bg-hover hover:text-ink'
                    }`}
                  >
                    <span className="flex-1">{s.label}</span>
                    {s.meta && <span className={`num text-[13px] ${active ? 'text-ink-2' : 'text-ink-3'}`}>{s.meta}</span>}
                    {s.done && !s.meta && <Check size={14} className="text-ok" />}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        <div ref={content} key={tab} className="min-w-0 [animation:page-in_160ms_ease-out]">
          {tab === 'overview' && <Overview h={h} go={setTab} now={now} />}
          {HIRING.some((x) => x.value === tab) && (
            <div className="mb-6">
              <Segmented value={tab} options={HIRING} onChange={setTab} />
            </div>
          )}
          {tab === 'jd' && <JobDescriptionView id={h.id} />}
          {tab === 'candidates' && <CandidatesView id={h.id} />}
          {tab === 'screening' && <Screening id={h.id} />}
          {tab === 'kit' && <InterviewKitView id={h.id} />}
          {tab === 'plan' && <PlanView h={h} />}
          {tab === 'clearance' && <ClearanceView h={h} successorActive={people?.find((p) => p.id === h.successor_id)?.status === 'active'} />}
          {tab === 'interview' && (redacted ? <InterviewProgress h={h} /> : <ExitInterview h={h} onChange={reload} />)}
          {tab === 'transfer' && !hidden.has('transfer') && <TransferView h={h} people={people ?? []} onChange={reload} />}
          {tab === 'ramp' &&
            !hidden.has('ramp') &&
            (h.successor ? (
              <RampPlan hid={h.id} mode="manager" successor={first(h.successor)} canApprove={!persona || (me?.reports.includes(h.employee_id) ?? false)} />
            ) : (
              <p className="text-ink-2">Choose a successor first. The plan is built for them.</p>
            ))}
        </div>
      </div>
    </>
  )
}
