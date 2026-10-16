import { Brain, Timer, UserRound } from '../../components/icons'
import { Link } from 'react-router'
import { RampPlan } from '../../components/RampPlan'
import type { Me } from '../../hooks/useViewAs'
import { StatBand } from '../../components/StatBand'
import { Button, Card, CardHeader, Chip, PageHeader } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { date, first } from '../../lib/format'
import type { Person } from '../../types/api'

/** The successor's home: the companion first (docs/product-strategy.md section 10.2). */
export function SuccessorHome({ me }: { me: Me }) {
  const from = me.succeeding[0]
  const { data: p } = useApi<Person>(`/people/${encodeURIComponent(me.id)}`)
  const inherited = (p?.knowledge ?? []).filter((k) => k.via === 'transfer')
  const transferred = from.status === 'transferred' || inherited.length > 0
  const ask = `/ask?as=${encodeURIComponent(me.id)}`

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={`Welcome, ${first(me.name)}`}
        sub={`You are taking over from ${from.employee}${from.title ? `, ${from.title}` : ''}.`}
        right={
          <Link to={ask}>
            <Button>Ask the companion</Button>
          </Link>
        }
      />

      <StatBand
        figures={[
          {
            label: 'Inherited knowledge',
            value: inherited.length,
            tone: transferred ? 'text-ok-text' : undefined,
            note: transferred ? `Approved by ${from.manager ? first(from.manager) : 'your manager'}` : 'After approval',
            icon: Brain,
          },
          { label: 'Handover completes', value: date(from.effective_at, true), icon: Timer },
          { label: 'Your manager', value: from.manager ? first(from.manager) : '–', icon: UserRound },
        ]}
      />

      <RampPlan hid={from.id} mode="successor" successor={first(me.name)} />

      <Card>
        <CardHeader title="What you inherited" meta={inherited.length} />
        {!transferred ? (
          <p className="text-ink-2">Nothing yet. It arrives when {from.manager ? first(from.manager) : 'the manager'} approves the handover.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {inherited.map((k) => (
              <li key={k.id} className="flex items-center justify-between gap-4 py-2.5">
                <span className="min-w-0 truncate">{k.title}</span>
                <Chip tone="accent">{k.kind}</Chip>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader title="Who to ask" />
        <ul className="flex flex-col gap-2 text-ink-2">
          <li>
            <span className="font-medium text-ink">{from.employee}</span>: until {date(from.effective_at)}
          </li>
          {from.manager && (
            <li>
              <span className="font-medium text-ink">{from.manager}</span>: your manager
            </li>
          )}
        </ul>
      </Card>
    </div>
  )
}
