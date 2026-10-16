import { Link } from 'react-router'
import { Avatar, Card, Chip, ErrorNote, PageHeader, PageSkeleton, THead } from '../components/ui'
import { Pager } from '../components/Pager'
import { useApi } from '../hooks/useApi'
import { usePaged } from '../hooks/usePaged'
import { date } from '../lib/format'
import type { HandoverRow } from '../types/api'

interface Meta {
  now: number
}

const COLS = 'minmax(0,1.6fr) minmax(0,1fr) 130px 120px'

export function HandoversPage() {
  const { data, error, loading } = useApi<HandoverRow[]>('/handovers')
  const { data: meta } = useApi<Meta>('/meta')
  const paged = usePaged(data ?? [], 10)
  if (loading && !data) return <PageSkeleton />
  if (error || !data) return <ErrorNote message={error ?? 'No data'} />
  const now = meta?.now ?? 0

  return (
    <>
      <PageHeader title="Handovers" />
      {data.length === 0 ? (
        <p className="border-t border-line py-6 text-[14px] text-ink-3">
          No handovers yet. Open someone in{' '}
          <Link to="/people" className="text-accent hover:underline">
            People
          </Link>{' '}
          and start one when they resign.
        </p>
      ) : (
        <Card className="px-5 pt-3 pb-1">
          <THead cols={COLS}>
            <span>Leaving</span>
            <span>Successor</span>
            <span>Last day</span>
            <span>Status</span>
          </THead>
          <ul>
            {paged.items.map((h) => {
              const days = now ? Math.max(0, Math.round((h.effective_at - now) / 86_400_000)) : 0
              const done = h.status === 'transferred'
              return (
                <li key={h.id} className="border-b border-line last:border-0">
                  <Link
                    to={`/handovers/${encodeURIComponent(h.id)}`}
                    className="-mx-2 grid h-14 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 rounded-[4px] px-2 transition-colors duration-150 hover:bg-app md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_130px_120px]"
                  >
                    <span className="flex min-w-0 items-center gap-2.5">
                      <Avatar name={h.employee} size={30} />
                      <span className="min-w-0">
                        <span className="block truncate text-[14px] font-medium">{h.employee}</span>
                        <span className="block truncate text-[13px] text-ink-3">{h.title}</span>
                      </span>
                    </span>
                    <span className="truncate text-[14px] max-md:hidden">{h.successor ?? <span className="text-soon">Not chosen</span>}</span>
                    <span className="text-[14px] max-md:hidden">
                      {done ? (
                        <span className="text-ink-3">–</span>
                      ) : (
                        <>
                          In <span className="num">{days}</span> days
                          <span className="num block text-[13px] text-ink-3">{date(h.effective_at, true)}</span>
                        </>
                      )}
                    </span>
                    <span>
                      {done ? (
                        <Chip>Handed over</Chip>
                      ) : h.open_gaps > 0 ? (
                        <Chip tone="soon">{h.open_gaps} open</Chip>
                      ) : (
                        <Chip tone="ok">Ready to approve</Chip>
                      )}
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
          <Pager p={paged} noun="handovers" />
        </Card>
      )}
    </>
  )
}
