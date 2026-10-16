import { useState } from 'react'

function niceMax(v: number): number {
  // Four even grid steps with round labels.
  const raw = Math.max(1, v) / 4
  const mag = Math.pow(10, Math.floor(Math.log10(raw)))
  const step = [1, 2, 2.5, 3, 4, 5, 6, 8, 10].map((m) => m * mag).find((m) => m >= raw) ?? 10 * mag
  return step * 4
}

/** Vertical bars with a light grid and hover values. */
export function ColumnChart({
  data,
  height = 168,
  unit = '',
}: {
  data: { key: string; label: string; value: number }[]
  height?: number
  unit?: string
}) {
  const [hover, setHover] = useState<number | null>(null)
  const max = niceMax(Math.max(0, ...data.map((d) => d.value)))
  const ticks = [max, (max * 3) / 4, max / 2, max / 4, 0]
  const every = Math.max(1, Math.ceil(data.length / 7))
  return (
    <div className="grid grid-cols-[28px_minmax(0,1fr)] gap-x-2">
      <div className="relative" style={{ height }}>
        {ticks.map((t, i) => (
          <span key={i} className="num absolute right-0 -translate-y-1/2 text-[12px] text-ink-3" style={{ top: `${(i / 4) * 100}%` }}>
            {Math.round(t)}
          </span>
        ))}
      </div>
      <div className="relative" style={{ height }} onMouseLeave={() => setHover(null)}>
        {ticks.map((_, i) => (
          <span key={i} className="absolute inset-x-0 h-px bg-hover" style={{ top: `${(i / 4) * 100}%` }} />
        ))}
        <div className="absolute inset-0 flex items-end gap-[3px]">
          {data.map((d, i) => (
            <div key={d.key} className="relative flex h-full flex-1 items-end" onMouseEnter={() => setHover(i)}>
              <div
                className={`w-full rounded-t-[3px] transition-colors duration-150 ${hover === i ? 'bg-s1' : 'bg-s2'}`}
                style={{ height: `${(d.value / max) * 100}%`, minHeight: d.value ? 2 : 0 }}
              />
              {hover === i && (
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 -translate-x-1/2 rounded-[4px] bg-ink px-2 py-1 text-[12px] whitespace-nowrap text-on-ink">
                  <span className="num font-medium">{d.value}</span>
                  {unit && ` ${unit}`} · {d.label}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div />
      <div className="mt-2 flex gap-[3px]">
        {data.map((d, i) => (
          <span key={d.key} className="num flex-1 text-center text-[12px] whitespace-nowrap text-ink-3">
            {i % every === 0 ? d.label : ''}
          </span>
        ))}
      </div>
    </div>
  )
}

/** One horizontal bar split into segments, a 2px gap between them. */
export function StackBar({ parts, max, height = 8 }: { parts: { value: number; color: string; label: string }[]; max: number; height?: number }) {
  return (
    <div className="flex w-full gap-[2px] overflow-hidden rounded-[1px] bg-hover" style={{ height }}>
      {parts.map((p) =>
        p.value > 0 ? (
          <span key={p.label} title={`${p.label}: ${p.value}`} className="h-full shrink-0" style={{ width: `${(p.value / max) * 100}%`, background: p.color }} />
        ) : null,
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- part-to-whole */

export interface Part {
  label: string
  value: number
  color: string
}

/** Ring split into parts, 2px gaps between them. The centre shows the total, or the hovered part. */
export function Donut({
  parts,
  size = 148,
  thickness = 16,
  caption = 'total',
  active,
  onActive,
}: {
  parts: Part[]
  size?: number
  thickness?: number
  caption?: string
  active?: number | null
  onActive?: (i: number | null) => void
}) {
  const [own, setOwn] = useState<number | null>(null)
  const hover = active !== undefined ? active : own
  const setHover = onActive ?? setOwn
  const total = parts.reduce((n, p) => n + p.value, 0)
  const r = (size - thickness - 4) / 2
  const c = 2 * Math.PI * r
  const gap = parts.filter((p) => p.value > 0).length > 1 ? 2 : 0
  const starts = parts.map((_, i) => parts.slice(0, i).reduce((n, p) => n + (p.value / (total || 1)) * c, 0))
  const focus = hover !== null ? parts[hover] : null
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} onMouseLeave={() => setHover(null)}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-hover)" strokeWidth={thickness} />
        {total > 0 &&
          parts.map((p, i) =>
            p.value > 0 ? (
              <circle
                key={p.label}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={p.color}
                strokeWidth={hover === i ? thickness + 4 : thickness}
                strokeDasharray={`${Math.max(0, (p.value / total) * c - gap)} ${c}`}
                strokeDashoffset={-starts[i]}
                opacity={hover !== null && hover !== i ? 0.35 : 1}
                className="transition-[opacity,stroke-width] duration-150"
                onMouseEnter={() => setHover(i)}
              />
            ) : null,
          )}
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="num text-[24px] leading-7 font-semibold tracking-[-0.02em]">{focus ? focus.value : total}</span>
        <span className="max-w-[80%] truncate text-[12px] text-ink-3">{focus ? focus.label : caption}</span>
      </div>
    </div>
  )
}

/** Donut beside a legend that names every part with its count and share. */
export function Breakdown({ parts, caption }: { parts: Part[]; caption?: string }) {
  const [hover, setHover] = useState<number | null>(null)
  const total = parts.reduce((n, p) => n + p.value, 0)
  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-5">
      <Donut parts={parts} caption={caption} active={hover} onActive={setHover} />
      <ul className="flex min-w-[180px] flex-1 flex-col gap-0.5" onMouseLeave={() => setHover(null)}>
        {parts.map((p, i) => (
          <li
            key={p.label}
            onMouseEnter={() => setHover(i)}
            className={`grid grid-cols-[10px_minmax(0,1fr)_auto_40px] items-center gap-3 rounded-[4px] px-2 py-1.5 text-[14px] transition-colors ${hover === i ? 'bg-app' : ''}`}
          >
            <span className="size-2.5 rounded-[3px]" style={{ background: p.color }} aria-hidden />
            <span className="truncate">{p.label}</span>
            <span className="num font-semibold">{p.value}</span>
            <span className="num text-right text-[13px] text-ink-3">{total ? Math.round((p.value / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ---------------------------------------------------------------- single value */

const TONE_STROKE = {
  risk: 'var(--color-risk)',
  soon: 'var(--color-soon-fill)',
  ok: 'var(--color-ok)',
  accent: 'var(--color-accent-fill)',
} as const
export type Tone = keyof typeof TONE_STROKE

/** A percentage as a ring, with an optional tick at the target. */
export function Gauge({
  value,
  target,
  tone = 'accent',
  size = 132,
  thickness = 12,
  label,
}: {
  value: number | null
  target?: number | null
  tone?: Tone
  size?: number
  thickness?: number
  label?: string
}) {
  const mid = size / 2
  const r = (size - thickness - 8) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, value ?? 0))
  const angle = ((target ?? 0) / 100) * 2 * Math.PI - Math.PI / 2
  const at = (d: number) => ({ x: mid + d * Math.cos(angle), y: mid + d * Math.sin(angle) })
  const inner = at(r - thickness / 2 - 3)
  const outer = at(r + thickness / 2 + 3)
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`${value ?? 'No value'}%${target ? `, target ${target}%` : ''}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={mid} cy={mid} r={r} fill="none" stroke="var(--color-hover)" strokeWidth={thickness} />
        {pct > 0 && (
          <circle
            cx={mid}
            cy={mid}
            r={r}
            fill="none"
            stroke={TONE_STROKE[tone]}
            strokeWidth={thickness}
            strokeLinecap="round"
            strokeDasharray={`${(pct / 100) * c} ${c}`}
            transform={`rotate(-90 ${mid} ${mid})`}
          />
        )}
        {target ? <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="var(--color-ink)" strokeWidth={2} strokeLinecap="round" /> : null}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-[26px] leading-8 font-semibold tracking-[-0.02em]">{value === null ? '–' : `${value}%`}</span>
        {label && <span className="text-[12px] text-ink-3">{label}</span>}
      </div>
    </div>
  )
}

let sparkId = 0

/** A small trend line with a soft fill, for KPI tiles. No axes: the tile's number carries the value. */
export function Sparkline({ values, height = 36, color = 'var(--color-accent-fill)' }: { values: number[]; height?: number; color?: string }) {
  const [id] = useState(() => `spark-${++sparkId}`)
  if (values.length < 2) return null
  const max = Math.max(1, ...values)
  const w = 100
  const line = values.map((v, i) => `${(i / (values.length - 1)) * w},${height - 2 - (v / max) * (height - 4)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="block w-full" style={{ height }} aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.2" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${height} ${line} ${w},${height}`} fill={`url(#${id})`} />
      <polyline points={line} fill="none" stroke={color} strokeWidth={2} vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

/* ---------------------------------------------------------------- comparisons */

const TONE_FILL = { risk: 'bg-risk', soon: 'bg-soon-fill', ok: 'bg-ok', accent: 'bg-accent-fill' } as const

export interface HBarRow {
  key: string
  label: string
  value: number
  /** Quiet text after the value, e.g. "3/9 solo". */
  sub?: string
  tone?: Tone
}

/** Labelled horizontal bars on one scale, with an optional target line. */
export function HBars({
  rows,
  max,
  target,
  unit = '',
  labelWidth = 120,
}: {
  rows: HBarRow[]
  max?: number
  target?: number
  unit?: string
  labelWidth?: number
}) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value))
  // A fixed value column keeps every track the same length, so the target line stays straight.
  const valueCol = rows.some((r) => r.sub) ? 112 : 48
  return (
    <div>
      <ul className="-mx-2 flex flex-col gap-0.5">
        {rows.map((r) => (
          <li
            key={r.key}
            className="grid items-center gap-4 rounded-[4px] px-2 py-1.5 transition-colors hover:bg-app"
            style={{ gridTemplateColumns: `${labelWidth}px minmax(0,1fr) ${valueCol}px` }}
          >
            <span className="truncate text-[14px]">{r.label}</span>
            <span className="relative block h-2 rounded-[1px] bg-hover">
              <span
                className={`absolute inset-y-0 left-0 rounded-[1px] ${TONE_FILL[r.tone ?? 'accent']}`}
                style={{ width: `${Math.min(100, (r.value / top) * 100)}%`, minWidth: r.value ? 4 : 0 }}
              />
              {target !== undefined && <span className="absolute -inset-y-1 w-0.5 rounded-full bg-ink" style={{ left: `calc(${(target / top) * 100}% - 1px)` }} aria-hidden />}
            </span>
            <span className="num text-right text-[13px] whitespace-nowrap">
              <span className="font-semibold text-ink">
                {r.value}
                {unit}
              </span>
              {r.sub && <span className="ml-1.5 text-ink-3">{r.sub}</span>}
            </span>
          </li>
        ))}
      </ul>
      {target !== undefined && (
        <div className="mt-2 flex items-center gap-1.5 text-[12px] text-ink-3">
          <span className="h-3 w-0.5 rounded-full bg-ink" aria-hidden />
          Target {target}
          {unit}
        </div>
      )}
    </div>
  )
}

/** Counts per ordered step (the exit pipeline), as a row of columns on one scale. */
export function StepBars({ steps, height = 56 }: { steps: { key: string; label: string; value: number }[]; height?: number }) {
  const max = Math.max(1, ...steps.map((s) => s.value))
  return (
    <ol className="grid gap-px overflow-hidden rounded-[4px] bg-line shadow-[0_0_0_1px_var(--color-line)]" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0,1fr))` }} aria-label="Handovers per stage">
      {steps.map((s, i) => (
        <li key={s.key} className="flex min-w-0 flex-col justify-between gap-2 bg-page px-3 pt-2.5 pb-2" style={{ minHeight: height + 28 }}>
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate font-mono text-[10.5px] tracking-[0.035em] text-ink-3 uppercase">
              {i + 1} · {s.label}
            </span>
          </span>
          <span className="flex items-end justify-between gap-2">
            <span className={`num text-[22px] leading-7 font-semibold tracking-[-0.02em] ${s.value ? 'text-ink' : 'text-strong'}`}>{s.value}</span>
            <span className="mb-1.5 h-1 w-10 rounded-[1px] bg-hover">
              <span className="block h-full rounded-[1px] bg-accent-fill" style={{ width: `${(s.value / max) * 100}%` }} />
            </span>
          </span>
        </li>
      ))}
    </ol>
  )
}
