import { ChatCircleDots, Hourglass, KeyRound, Lock } from '../../components/icons'
import { Link } from 'react-router'
import type { Me } from '../../hooks/useViewAs'
import { StatBand } from '../../components/StatBand'
import { CapturePlan } from '../../components/CapturePlan'
import { Card, CardHeader, Chip, ErrorNote, PageHeader, PageSkeleton } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { date, daysBetween, first } from '../../lib/format'
import type { Handover, Person } from '../../types/api'
import { ExitInterview } from '../handover/ExitInterview'

/** The leaver's home: one checklist (docs/product-strategy.md section 10.2). */
export function LeaverHome({ me }: { me: Me }) {
  const summary = me.leaving[0]
  const { data: h, error, loading, reload } = useApi<Handover>(`/handovers/${encodeURIComponent(summary.id)}`)
  const { data: meta } = useApi<{ now: number }>('/meta')
  const { data: p } = useApi<Person>(`/people/${encodeURIComponent(me.id)}`)

  if (loading && !h) return <PageSkeleton />
  if (error) return <ErrorNote message={error} />
  if (!h) return null

  // Same count as the Overview and the interview list: interview gaps that are not dismissed.
  const questions = h.gaps.filter((g) => g.interview && g.status !== 'dismissed')
  const total = questions.length
  const answered = questions.filter((g) => g.status === 'answered').length
  const daysLeft = h.effective_at && meta ? Math.max(0, daysBetween(meta.now, h.effective_at)) : null
  const soleContacts = (p?.stakeholders ?? []).filter((s) => s.other_contacts.length === 0)
  const knowledge = p?.knowledge ?? []
  const privateCount = knowledge.filter((k) => k.private).length
  const soleAccounts = (p?.accounts ?? []).filter((a) => a.other_admins.length === 0).length

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={`Your handover, ${first(me.name)}`}
        sub={`Last day ${date(h.effective_at)} · successor ${h.successor ?? 'not chosen yet'}`}
      />

      <StatBand
        figures={[
          { label: 'Days left', value: daysLeft ?? '–', tone: daysLeft !== null && daysLeft < 7 ? 'text-risk-text' : undefined, icon: Hourglass },
          {
            label: 'Questions answered',
            value: `${answered}/${total}`,
            tone: total > 0 && answered === total ? 'text-ok-text' : 'text-soon',
            icon: ChatCircleDots,
            meter: total ? { value: answered, max: total } : undefined,
          },
          {
            label: 'Accounts only you admin',
            value: soleAccounts,
            note: soleAccounts ? 'You keep access until your last day' : undefined,
            tone: soleAccounts ? 'text-risk-text' : undefined,
            icon: KeyRound,
          },
          { label: 'Kept private', value: privateCount, note: `of ${knowledge.length} items`, href: '/me', icon: Lock },
        ]}
      />

      <CapturePlan hid={h.id} compact />

      <Card>
        <CardHeader title="Questions only you can answer" meta={`${answered}/${total}`} />
        <ExitInterview h={h} onChange={reload} />
      </Card>

      <Card>
        <CardHeader
          title="What moves to your successor"
          right={<Link to="/me" className="text-accent">Review</Link>}
        />
        <p className="text-ink-2">
          {knowledge.length - privateCount} items can move to {h.successor ? first(h.successor) : 'your successor'} once{' '}
          {h.manager ? first(h.manager) : 'your manager'} approves. Items you keep private never move.
        </p>
      </Card>

      <Card>
        <CardHeader title="People to introduce" meta={soleContacts.length} />
        {soleContacts.length === 0 ? (
          <p className="text-ink-3">No external contacts depend only on you.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {soleContacts.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-4 py-2.5">
                <span>
                  <span className="font-medium">{s.name}</span>
                  <span className="text-ink-3"> · {s.org}</span>
                </span>
                <Chip tone="soon">Only you</Chip>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
