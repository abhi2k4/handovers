import { AlertTriangle, CheckCircle2, Inbox } from './icons'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useApi } from '../hooks/useApi'
import { date, first } from '../lib/format'
import { ColumnChart } from './charts'
import { Avatar, Card, CardHeader, Pills } from './ui'

/** The parts of GET /dashboard the trend cards read. */
interface Trends {
  now: number
  health: Record<'unexplained' | 'contradictions' | 'procedures' | 'undocumented', { count: number; example: string | null }>
  activity: { start: number; days: Record<string, number>; total: number; review: number }
  joiners: { id: string; name: string; title: string; starts: number; inherits_from: string | null }[]
}

const DAY = 86_400_000
const dayLabel = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })
type Range = '30d' | '12w' | '26w'

/** Memory growth, knowledge health and joiners: trends that live on Insights, not the daily Overview. */
export function TrendCards() {
  const { data: d } = useApi<Trends>('/dashboard')
  if (!d) return null
  return (
    <>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
        <MemoryGrowth d={d} />
        <KnowledgeHealth d={d} />
      </div>
      <Joining joiners={d.joiners} />
    </>
  )
}

function MemoryGrowth({ d }: { d: Trends }) {
  const [range, setRange] = useState<Range>('12w')
  const data = useMemo(() => {
    const at = (ms: number) => d.activity.days[new Date(ms).toISOString().slice(0, 10)] ?? 0
    const end = d.now - (d.now % DAY)
    if (range === '30d') {
      return Array.from({ length: 30 }, (_, i) => {
        const t = end - (29 - i) * DAY
        return { key: String(t), label: dayLabel.format(t), value: at(t) }
      })
    }
    const weeks = range === '12w' ? 12 : 26
    return Array.from({ length: weeks }, (_, i) => {
      const startW = end - (weeks - i) * 7 * DAY + DAY
      let n = 0
      for (let k = 0; k < 7; k++) n += at(startW + k * DAY)
      return { key: String(startW), label: dayLabel.format(startW), value: n }
    })
  }, [d, range])
  const sum = data.reduce((n, x) => n + x.value, 0)
  return (
    <Card>
      <CardHeader
        title="Memory"
        right={
          <Pills
            value={range}
            onChange={setRange}
            options={[
              { value: '30d', label: '30 days' },
              { value: '12w', label: '12 weeks' },
              { value: '26w', label: '6 months' },
            ]}
          />
        }
      />
      <div className="mb-5 flex items-baseline gap-2">
        <span className="num text-[26px] leading-8 font-semibold tracking-[-0.02em]">{sum}</span>
        <span className="text-[14px] text-ink-3">work records learned</span>
      </div>
      <ColumnChart data={data} unit="records" />
    </Card>
  )
}

const HEALTH: { key: keyof Trends['health']; label: string }[] = [
  { key: 'unexplained', label: 'Settings with no reason' },
  { key: 'undocumented', label: 'Decisions only in a head' },
  { key: 'procedures', label: 'Fixes never written down' },
  { key: 'contradictions', label: 'Sources that disagree' },
]

function KnowledgeHealth({ d }: { d: Trends }) {
  return (
    <Card>
      <CardHeader title="Knowledge health" />
      <ul className="flex flex-col gap-1">
        {HEALTH.map((h) => {
          const n = d.health[h.key].count
          return (
            <li key={h.key} className="flex items-start gap-3 py-2 text-[14px]">
              {n ? (
                <AlertTriangle size={16} strokeWidth={1.9} className="mt-px shrink-0 text-soon-fill" />
              ) : (
                <CheckCircle2 size={16} strokeWidth={1.9} className="mt-px shrink-0 text-ok" />
              )}
              <span className="min-w-0 flex-1">
                <span className="block">{h.label}</span>
                <span className="block truncate text-[13px] text-ink-3">{n ? d.health[h.key].example : 'None found'}</span>
              </span>
              <span className={`num ${n ? 'font-semibold' : 'text-ink-3'}`}>{n}</span>
            </li>
          )
        })}
      </ul>
      {d.activity.review > 0 && (
        <>
          <div className="my-3 h-px bg-line" />
          <Link to="/sources" className="-mx-2 flex h-9 items-center gap-3 rounded-[4px] px-2 text-[14px] hover:bg-app">
            <Inbox size={16} strokeWidth={1.9} className="text-accent" />
            <span className="flex-1">To review</span>
            <span className="num font-semibold">{d.activity.review}</span>
          </Link>
        </>
      )}
    </Card>
  )
}

function Joining({ joiners }: { joiners: Trends['joiners'] }) {
  if (!joiners.length) return null
  return (
    <Card>
      <CardHeader title="Joining" meta={joiners.length} />
      <ul className="-mx-2 grid sm:grid-cols-2">
        {joiners.map((j) => (
          <li key={j.id}>
            <Link to={`/people/${encodeURIComponent(j.id)}`} className="flex items-center gap-2.5 rounded-[4px] px-2 py-1.5 hover:bg-app">
              <Avatar name={j.name} size={28} muted />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[14px] font-medium">{j.name}</span>
                <span className="block truncate text-[13px] text-ink-3">{j.inherits_from ? `Takes over from ${first(j.inherits_from)}` : j.title}</span>
              </span>
              <span className="num text-[13px] text-ink-3">{date(j.starts, true)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  )
}
