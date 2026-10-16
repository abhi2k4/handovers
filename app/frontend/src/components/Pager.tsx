import { ChevronLeft, ChevronRight } from './icons'
import type { Paged } from '../hooks/usePaged'

/** "11–20 of 24" with previous / next and page numbers. Hidden when everything fits on one page. */
export function Pager<T>({ p, noun = 'items' }: { p: Paged<T>; noun?: string }) {
  if (p.pages <= 1) return null
  const numbers = Array.from({ length: p.pages }, (_, i) => i)
  const btn = 'flex h-7 min-w-7 items-center justify-center rounded-[4px] px-2 text-[13px] transition-colors'
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3 border-t border-line pt-3 pb-2">
      <span className="num text-[13px] text-ink-3">
        {p.from}–{p.to} of {p.total} {noun}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => p.setPage(p.page - 1)}
          disabled={p.page === 0}
          aria-label="Previous page"
          className={`${btn} text-ink-2 hover:bg-hover disabled:opacity-30 disabled:hover:bg-transparent`}
        >
          <ChevronLeft size={14} />
        </button>
        {p.pages <= 7 &&
          numbers.map((n) => (
            <button
              key={n}
              onClick={() => p.setPage(n)}
              aria-current={n === p.page ? 'page' : undefined}
              className={`${btn} num ${n === p.page ? 'bg-selected font-medium text-ink' : 'text-ink-2 hover:bg-hover'}`}
            >
              {n + 1}
            </button>
          ))}
        {p.pages > 7 && (
          <span className="num px-2 text-[13px] text-ink-2">
            {p.page + 1} / {p.pages}
          </span>
        )}
        <button
          onClick={() => p.setPage(p.page + 1)}
          disabled={p.page === p.pages - 1}
          aria-label="Next page"
          className={`${btn} text-ink-2 hover:bg-hover disabled:opacity-30 disabled:hover:bg-transparent`}
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </nav>
  )
}
