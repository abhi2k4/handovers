import type { ComponentType, ReactNode } from 'react'
import { Link } from 'react-router'
import { Sparkline } from './charts'

type Icon = ComponentType<{ size?: number; weight?: 'regular' | 'duotone'; className?: string }>

export interface Figure {
  label: string
  value: ReactNode
  note?: string
  /** Text colour class for the value, e.g. `text-risk-text`. Also tints the tile's icon. */
  tone?: string
  href?: string
  icon?: Icon
  /** A meter under the number: progress towards `max`, with an optional target tick. */
  meter?: { value: number; max: number; target?: number | null }
  /** A small trend line under the number. */
  spark?: number[]
}

// The tone shows as a short rule above the figure, not a coloured icon tile.
const RULE: Record<string, string> = {
  'text-risk-text': 'bg-risk',
  'text-soon': 'bg-soon-fill',
  'text-ok-text': 'bg-ok',
}

const METER_FILL: Record<string, string> = {
  'text-risk-text': 'bg-risk',
  'text-soon': 'bg-soon-fill',
  'text-ok-text': 'bg-ok',
}

function Body({ f, compact }: { f: Figure; compact: boolean }) {
  const Icon = f.icon
  const m = f.meter
  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <div className="eyebrow">{f.label}</div>
        {Icon && !compact && <Icon size={14} className="shrink-0 text-ink-3" />}
      </div>
      <div className={`num ${compact ? 'mt-1' : 'mt-2'} text-[28px] leading-8 font-semibold tracking-[-0.03em] ${f.tone ?? 'text-ink'}`}>{f.value}</div>
      {f.note && <div className="mt-0.5 truncate text-[12.5px] text-ink-3">{f.note}</div>}
      {m && (
        <div className="relative mt-3 h-1 rounded-[1px] bg-hover" aria-hidden>
          <div
            className={`absolute inset-y-0 left-0 rounded-[1px] ${METER_FILL[f.tone ?? ''] ?? 'bg-accent-fill'}`}
            style={{ width: `${m.max > 0 ? Math.min(100, (m.value / m.max) * 100) : 0}%`, minWidth: m.value ? 3 : 0 }}
          />
          {m.target ? <div className="absolute -inset-y-[3px] w-px bg-ink" style={{ left: `${(m.target / m.max) * 100}%` }} /> : null}
        </div>
      )}
      {f.spark && (
        <div className="mt-2">
          <Sparkline values={f.spark} height={28} />
        </div>
      )}
    </>
  )
}

const COLS: Record<number, string> = { 1: 'lg:grid-cols-1', 2: 'lg:grid-cols-2', 3: 'lg:grid-cols-3', 4: 'lg:grid-cols-4', 5: 'lg:grid-cols-5', 6: 'lg:grid-cols-6' }

/**
 * Key numbers. `tiles` (default): one card per number, with an icon, a meter or a trend line.
 * `band`: one box split by hairlines, for numbers inside a card. Two per row on small screens.
 */
export function StatBand({ figures, variant = 'tiles' }: { figures: Figure[]; variant?: 'tiles' | 'band' }) {
  if (variant === 'band') {
    return (
      <section className="grid grid-cols-2 overflow-hidden rounded-[4px] bg-app shadow-[inset_0_0_0_1px_var(--color-line)] lg:grid-flow-col lg:auto-cols-fr lg:grid-cols-none">
        {figures.map((f, i) => {
          // Hairlines: left of every figure except the first in its row; above the second row on small screens.
          const cls = `block px-4 py-3.5 border-line ${i % 2 === 1 ? 'border-l' : ''} ${i >= 2 ? 'max-lg:border-t' : ''} ${i > 0 ? 'lg:border-l' : ''}`
          return f.href ? (
            <Link key={f.label} to={f.href} className={`${cls} transition-colors hover:bg-hover`}>
              <Body f={f} compact />
            </Link>
          ) : (
            <div key={f.label} className={cls}>
              <Body f={f} compact />
            </div>
          )
        })}
      </section>
    )
  }
  return (
    <section className={`grid grid-cols-1 overflow-hidden rounded-[6px] bg-page shadow-card sm:grid-cols-2 ${COLS[Math.min(6, figures.length)]}`}>
      {figures.map((f, i) => {
        // One instrument panel split by hairlines; each figure's tone is a short rule above it.
        const cls = `relative flex flex-col px-5 pt-4 pb-4 border-line ${i > 0 ? 'max-sm:border-t' : ''} ${i % 2 === 1 ? 'sm:border-l' : ''} ${i >= 2 ? 'sm:max-lg:border-t' : ''} ${i > 0 ? 'lg:border-l' : ''}`
        const rule = RULE[f.tone ?? ''] && <span aria-hidden className={`absolute top-0 left-5 h-[2px] w-6 ${RULE[f.tone ?? '']}`} />
        return f.href ? (
          <Link key={f.label} to={f.href} className={`${cls} transition-colors duration-150 hover:bg-app`}>
            {rule}
            <Body f={f} compact={false} />
          </Link>
        ) : (
          <div key={f.label} className={cls}>
            {rule}
            <Body f={f} compact={false} />
          </div>
        )
      })}
    </section>
  )
}
