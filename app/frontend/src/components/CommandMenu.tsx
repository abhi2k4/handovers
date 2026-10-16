import { CornerDownLeft, Search } from './icons'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useApi } from '../hooks/useApi'
import { useNav } from '../layouts/nav'
import type { HandoverRow, PersonRow } from '../types/api'
import { Avatar, Kbd } from './ui'

interface Item {
  id: string
  label: string
  hint: string
  group: string
  href: string
  person?: string
}

/** ⌘K / Ctrl K: jump to anyone, any handover, or an action. */
export function CommandMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const { data: people } = useApi<PersonRow[]>(open ? '/people' : null)
  const { data: handovers } = useApi<HandoverRow[]>(open ? '/handovers' : null)
  const pages = useNav()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const items = useMemo<Item[]>(() => {
    const all: Item[] = [
      ...pages.map((n) => ({ id: `go:${n.to}`, label: n.label, hint: 'Go to', group: 'Go to', href: n.to })),
      ...(handovers ?? []).map((h) => ({
        id: `h:${h.id}`,
        label: `${h.employee}'s handover`,
        hint: h.status === 'transferred' ? 'Handed over' : 'In progress',
        group: 'Handovers',
        href: `/handovers/${encodeURIComponent(h.id)}`,
        person: h.employee,
      })),
      ...(people ?? []).map((p) => ({
        id: `p:${p.id}`,
        label: p.name,
        hint: p.title,
        group: 'People',
        href: `/people/${encodeURIComponent(p.id)}`,
        person: p.name,
      })),
      ...(people ?? [])
        .filter((p) => p.status !== 'departed')
        .map((p) => ({
          id: `a:${p.id}`,
          label: `Ask as ${p.name}`,
          hint: 'Companion',
          group: 'Actions',
          href: `/ask?as=${encodeURIComponent(p.id)}`,
          person: p.name,
        })),
    ]
    const q = query.trim().toLowerCase()
    if (!q) return all.filter((i) => i.group !== 'Actions').slice(0, 12)
    return all.filter((i) => `${i.label} ${i.hint}`.toLowerCase().includes(q)).slice(0, 12)
  }, [pages, people, handovers, query])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  if (!open) return null

  function go(item: Item | undefined) {
    if (!item) return
    onClose()
    navigate(item.href)
  }

  let lastGroup = ''
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-[rgba(33,32,28,0.08)] px-4 pt-[12vh]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-label="Command menu"
        className="w-full max-w-lg overflow-hidden rounded-[6px] bg-page shadow-[0_0_0_1px_var(--color-line),0_1px_2px_rgba(0,0,0,0.06),0_8px_24px_rgba(0,0,0,0.08)]"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 border-b border-line px-4">
          <Search size={15} strokeWidth={1.75} className="text-ink-3" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActive(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setActive((a) => Math.min(a + 1, items.length - 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setActive((a) => Math.max(a - 1, 0))
              } else if (e.key === 'Enter') {
                go(items[active])
              } else if (e.key === 'Escape') {
                onClose()
              }
            }}
            placeholder="Search people, handovers, actions"
            className="h-12 flex-1 bg-transparent text-[15px] outline-none placeholder:text-ink-3"
          />
          <Kbd>esc</Kbd>
        </div>
        <ul className="max-h-[52vh] overflow-y-auto p-1.5">
          {items.length === 0 && <li className="px-3 py-6 text-center text-[14px] text-ink-3">No matches</li>}
          {items.map((item, i) => {
            const header = item.group !== lastGroup ? item.group : null
            lastGroup = item.group
            return (
              <li key={item.id}>
                {header && <div className="px-2.5 pt-2.5 pb-1 text-[12px] text-ink-3">{header}</div>}
                <button
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(item)}
                  className={`flex w-full items-center gap-3 rounded-[6px] px-2.5 py-2 text-left text-[14px] ${
                    i === active ? 'bg-hover' : ''
                  }`}
                >
                  {item.person ? <Avatar name={item.person} size={20} /> : <span className="size-5" />}
                  <span className="flex-1 truncate">{item.label}</span>
                  <span className="truncate text-[13px] text-ink-3">{item.hint}</span>
                  {i === active && <CornerDownLeft size={13} className="text-ink-3" />}
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
