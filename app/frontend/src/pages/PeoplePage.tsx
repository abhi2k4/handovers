import { Search } from '../components/icons'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { Avatar, Bar, Card, Chip, ErrorNote, PageHeader, PageSkeleton, Pills, THead } from '../components/ui'
import { Pager } from '../components/Pager'
import { useApi } from '../hooks/useApi'
import { usePaged } from '../hooks/usePaged'
import type { PersonRow } from '../types/api'

type Filter = 'all' | 'risk' | 'leaving' | 'joining'
const COLS = 'minmax(0,2fr) minmax(0,1fr) minmax(0,1.3fr) 96px'

function status(p: PersonRow) {
  if (p.status === 'incoming') return <Chip tone="accent">Joining</Chip>
  if (p.status === 'departed') return <Chip>Left</Chip>
  if (p.handover_id) return <Chip tone="risk">Leaving</Chip>
  return <span className="text-[13px] text-ink-3">Active</span>
}

export function PeoplePage() {
  const { data, error, loading } = useApi<PersonRow[]>('/people')
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')

  const groups = useMemo(() => {
    const all = data ?? []
    return {
      all,
      risk: [...all].filter((p) => p.risk > 0 && p.status === 'active').sort((a, b) => b.risk - a.risk),
      leaving: all.filter((p) => p.handover_id && p.status === 'active'),
      joining: all.filter((p) => p.status === 'incoming'),
    }
  }, [data])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = groups[filter]
    return q ? list.filter((p) => `${p.name} ${p.title} ${p.team}`.toLowerCase().includes(q)) : list
  }, [groups, filter, query])

  const paged = usePaged(rows, 10, `${filter}|${query}`)

  if (loading && !data) return <PageSkeleton />
  if (error || !data) return <ErrorNote message={error ?? 'No data'} />
  const max = Math.max(1, ...data.map((p) => p.risk))

  return (
    <>
      <PageHeader title="People" />
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Pills
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: `Everyone ${groups.all.filter((p) => p.status !== 'departed').length}` },
            { value: 'risk', label: `Hold the most ${groups.risk.length}` },
            { value: 'leaving', label: `Leaving ${groups.leaving.length}` },
            { value: 'joining', label: `Joining ${groups.joining.length}` },
          ]}
        />
        <label className="flex h-8 w-60 items-center gap-2 rounded-[4px] px-2.5 shadow-[inset_0_0_0_1px_var(--color-control)] focus-within:shadow-[inset_0_0_0_1px_var(--color-accent-fill),0_0_0_3px_var(--color-accent-soft)]">
          <Search size={13} strokeWidth={1.75} className="text-ink-3" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter"
            className="flex-1 bg-transparent text-[14px] outline-none placeholder:text-ink-3"
          />
        </label>
      </div>

      <Card className="px-5 pt-3 pb-1">
      <THead cols={COLS}>
        <span>Name</span>
        <span>Team</span>
        <span>Holds on their own</span>
        <span>Status</span>
      </THead>
      <ul>
        {paged.items.map((p) => (
          <li key={p.id} className="border-b border-line last:border-0">
            <Link
              to={`/people/${encodeURIComponent(p.id)}`}
              className="-mx-2 grid h-14 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 rounded-[4px] px-2 transition-colors duration-150 hover:bg-app md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.3fr)_96px]"
            >
              <span className="flex min-w-0 items-center gap-2.5">
                <Avatar name={p.name} size={30} muted={p.status !== 'active'} />
                <span className="min-w-0">
                  <span className="block truncate text-[14px] font-medium">{p.name}</span>
                  <span className="block truncate text-[13px] text-ink-3">{p.title}</span>
                </span>
              </span>
              <span className="truncate text-[14px] text-ink-2 max-md:hidden">{p.team}</span>
              <span className="flex items-center gap-3 max-md:hidden">
                {p.status === 'active' && p.risk > 0 ? (
                  <>
                    <span className="w-32">
                      <Bar value={p.risk} max={max} risk={!!p.handover_id} />
                    </span>
                    <span className="num text-[14px] font-semibold">{p.risk}</span>
                  </>
                ) : (
                  <span className="text-[13px] text-ink-3">–</span>
                )}
              </span>
              <span>{status(p)}</span>
            </Link>
          </li>
        ))}
        {rows.length === 0 && <li className="py-8 text-center text-[14px] text-ink-3">No one matches.</li>}
      </ul>
      <Pager p={paged} noun="people" />
      </Card>
    </>
  )
}
