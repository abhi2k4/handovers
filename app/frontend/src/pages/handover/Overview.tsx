import { CapturePlan } from '../../components/CapturePlan'
import { Lock } from '../../components/icons'
import { Notes } from '../../components/Notes'
import { ReadinessCard } from '../../components/Readiness'
import { StatBand } from '../../components/StatBand'
import { Bar, Card, CardHeader, Chip } from '../../components/ui'
import type { Handover } from '../../types/api'
import type { Tab } from './HandoverPage'

const RULE_TAB: Record<string, Tab> = { G7A: 'plan', G7S: 'plan', G7R: 'plan' }
// What a redacted item is, for HR, who sees that knowledge is at risk but not what it says.
const KIND_NAME: Record<string, string> = { Decision: 'A decision', Claim: 'A setting or figure', Knowledge: 'Know-how', Question: 'A question' }

export function Overview({ h, go, now }: { h: Handover; go: (t: Tab) => void; now: number }) {
  const access = h.gaps.filter((g) => g.rule === 'G7A' && g.resolution !== 'reassigned')
  const work = h.gaps.filter((g) => g.target_kind === 'Responsibility')
  const people = h.gaps.filter((g) => g.rule === 'G7S')
  const unknowns = h.gaps.filter((g) => ['G1', 'G2', 'G4', 'G6', 'G8'].includes(g.rule))
  const lost = h.gaps.filter((g) => !['G7R', 'M', 'Q'].includes(g.rule))
  const captured = lost.filter((g) => g.status === 'answered').length

  return (
    <div className="flex flex-col gap-4">
      <StatBand
        figures={[
          { label: 'Work only they do', value: work.length, tone: work.length ? 'text-risk-text' : undefined },
          { label: 'Sole admin accounts', value: access.length, tone: access.length ? 'text-risk-text' : undefined },
          { label: 'Only contact for', value: people.length, tone: people.length ? 'text-risk-text' : undefined },
          { label: 'Not written down', value: unknowns.length, tone: unknowns.length ? 'text-soon' : undefined },
        ]}
      />

      {/* Keyed on the successor: choosing one in the header (a readiness step) reloads the card. */}
      <ReadinessCard key={h.successor_id ?? 'none'} hid={h.id} />

      {h.status !== 'cancelled' && h.employee_status !== 'departed' && <CapturePlan hid={h.id} onOpen={(t) => go(t as Tab)} />}

      {h.can?.notes && <Notes hid={h.id} now={now} />}

      <Card>
        <CardHeader
          title="What could be lost"
          meta={lost.length}
          right={
            <span className="flex items-center gap-2">
              <span className="w-24">
                <Bar value={captured} max={Math.max(1, lost.length)} />
              </span>
              <span className="num">
                {captured}/{lost.length} captured
              </span>
            </span>
          }
        />
        <ul className="-mx-2 flex flex-col">
          {lost.map((g) => (
            <li key={g.id}>
              <button
                onClick={() => go(RULE_TAB[g.rule] ?? 'interview')}
                className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-4 rounded-[4px] px-2 py-2 text-left transition-colors duration-150 hover:bg-app"
              >
                <span className="min-w-0">
                  {g.redacted && g.title === g.label ? (
                    <>
                      <span className="block truncate text-[14px] font-medium">{KIND_NAME[g.target_kind] ?? 'An item'}: {g.label.toLowerCase()}</span>
                      <span className="flex items-center gap-1 text-[13px] text-ink-3">
                        <Lock size={12} aria-hidden /> Only the leaver and the approver see what it says
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="block truncate text-[14px] font-medium">{g.title}</span>
                      {g.title !== g.label && <span className="block text-[13px] text-ink-3">{g.label}</span>}
                    </>
                  )}
                </span>
                {g.status === 'answered' ? (
                  <Chip tone="ok">Captured</Chip>
                ) : g.status === 'dismissed' ? (
                  <Chip>Resolved</Chip>
                ) : (
                  <Chip tone={g.rule === 'G7A' ? 'risk' : 'soon'}>Open</Chip>
                )}
              </button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
