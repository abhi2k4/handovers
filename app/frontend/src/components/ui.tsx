import { Link } from 'react-router'
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { initials } from '../lib/format'
import { ChevronDown } from './icons'

/* ---------------------------------------------------------------- actions */

type Variant = 'primary' | 'secondary' | 'ghost' | 'link'

const buttonVariants: Record<Variant, string> = {
  primary: 'h-8 px-3 bg-ink text-on-ink hover:opacity-90 active:translate-y-px',
  secondary: 'h-8 px-3 bg-page text-ink shadow-[inset_0_0_0_1px_var(--color-control)] hover:bg-hover active:translate-y-px',
  ghost: 'h-8 px-2.5 text-ink-2 hover:bg-hover hover:text-ink',
  link: 'text-accent hover:underline underline-offset-2',
}

export function Button({
  variant = 'primary',
  className = '',
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={`inline-flex shrink-0 items-center justify-center gap-1.5 rounded-[4px] text-[13px] font-medium transition-[background-color,transform,box-shadow] duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${buttonVariants[variant]} ${className}`}
      {...props}
    />
  )
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-[2px] px-1 font-mono text-[10.5px] text-ink-3 shadow-[inset_0_0_0_1px_var(--color-line)]">
      {children}
    </kbd>
  )
}

/* ---------------------------------------------------------------- structure */

/** A section is separated by space and a title, not a box. */
export function Section({
  title,
  meta,
  action,
  children,
  className = '',
}: {
  title: ReactNode
  meta?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={className}>
      <header className="mb-3 flex items-baseline justify-between gap-4 border-b border-line pb-2">
        <h2 className="text-[14px] leading-5 font-semibold tracking-[-0.005em]">
          {title}
          {meta !== undefined && <span className="ml-2 font-mono text-[12px] font-normal text-ink-3">{meta}</span>}
        </h2>
        {action && <div className="text-[13px] text-ink-3">{action}</div>}
      </header>
      {children}
    </section>
  )
}

/** Grouping container, for content that is one unit (a document, a form). */
export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-[4px] shadow-[inset_0_0_0_1px_var(--color-line)] ${className}`}>{children}</div>
}

export function PageHeader({
  title,
  sub,
  right,
}: {
  title: ReactNode
  sub?: ReactNode
  right?: ReactNode
}) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[24px] leading-8 font-semibold tracking-[-0.025em]">{title}</h1>
        {sub && <p className="mt-1 max-w-2xl text-[14px] text-ink-2">{sub}</p>}
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </header>
  )
}

export function Breadcrumb({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav className="mb-4 flex items-center gap-1.5 font-mono text-[11.5px] tracking-[0.02em] text-ink-3">
      {items.map((i, n) => (
        <span key={i.label} className="flex items-center gap-1.5">
          {n > 0 && <span className="text-strong">/</span>}
          {i.href ? (
            <Link to={i.href} className="hover:text-ink">
              {i.label}
            </Link>
          ) : (
            <span className="text-ink-2">{i.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}

/** Table header row for grid-based tables. */
export function THead({ cols, children }: { cols: string; children: ReactNode }) {
  return (
    <div
      className="eyebrow grid items-center gap-4 border-b border-line pb-2 max-md:hidden"
      style={{ gridTemplateColumns: cols }}
    >
      {children}
    </div>
  )
}

/* ---------------------------------------------------------------- identity & status */

// A quiet tint per person (stable from their name), so a list of people reads at a glance.
const AVATAR_TINTS = [
  'bg-[#e8eefb] text-[#1d4ea8] dark:bg-[#17263f] dark:text-[#8db7ff]',
  'bg-[#e6f4ef] text-[#0f6b52] dark:bg-[#10291f] dark:text-[#6fd8b4]',
  'bg-[#fdeee6] text-[#a4471b] dark:bg-[#33190e] dark:text-[#f5a27c]',
  'bg-[#efebfb] text-[#4d3bb0] dark:bg-[#211b3d] dark:text-[#b3a6ff]',
  'bg-[#fbf3dc] text-[#80590a] dark:bg-[#2c2410] dark:text-[#e9c46a]',
  'bg-[#e9f3f9] text-[#1b6386] dark:bg-[#11263a] dark:text-[#7ec3e8]',
]

export function Avatar({ name, size = 24, muted = false }: { name: string; size?: number; muted?: boolean }) {
  let hash = 0
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  const tint = AVATAR_TINTS.at(hash % AVATAR_TINTS.length)
  return (
    <span
      aria-hidden
      style={{ width: size, height: size, fontSize: Math.max(10, Math.round(size * 0.38)) }}
      className={`inline-flex shrink-0 items-center justify-center rounded-[4px] font-semibold tracking-[0.02em] ${
        muted ? 'bg-app text-ink-3 shadow-[inset_0_0_0_1px_var(--color-line)]' : tint
      }`}
    >
      {initials(name)}
    </span>
  )
}

/* ---------------------------------------------------------------- data marks */

export function Bar({ value, max, risk = false, tone }: { value: number; max: number; risk?: boolean; tone?: 'accent' | 'risk' | 'soon' | 'ok' | 'quiet' }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const fill = { accent: 'bg-accent-fill', risk: 'bg-risk', soon: 'bg-soon-fill', ok: 'bg-ok', quiet: 'bg-mark' }[tone ?? (risk ? 'risk' : 'accent')]
  return (
    <span className="relative block h-1.5 w-full rounded-[1px] bg-hover">
      <span className={`absolute inset-y-0 left-0 rounded-[1px] ${fill}`} style={{ width: `${pct}%`, minWidth: value ? 3 : 0 }} />
    </span>
  )
}

/* ---------------------------------------------------------------- states */

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-[3px] bg-hover ${className}`} />
}

export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-8" role="status" aria-label="Loading">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-6 w-[min(560px,90%)]" />
      </div>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-9" />
          ))}
        </div>
        <Skeleton className="h-60" />
      </div>
    </div>
  )
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-12 text-[14px] text-ink-3" role="status">
      <span className="size-3.5 animate-spin rounded-full border-[1.5px] border-line border-t-ink-2" />
      {label}
    </div>
  )
}

export function ErrorNote({ message }: { message: string }) {
  return <p className="py-10 text-[14px] text-risk-text">{message}</p>
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-5 text-[14px] text-ink-3">{children}</p>
}

/* ---------------------------------------------------------------- inputs */

const field =
  'rounded-[4px] bg-page text-[14px] outline-none transition-shadow duration-150 shadow-[inset_0_0_0_1px_var(--color-control)] placeholder:text-ink-3 focus:shadow-[inset_0_0_0_1px_var(--color-accent-fill),0_0_0_3px_var(--color-accent-soft)]'

/** Native select (keyboard and screen readers for free) with our own caret, so text never runs under it. */
export function Select({ className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <span className={`relative inline-flex max-w-full min-w-0 ${className}`}>
      <select
        {...props}
        className={`h-8 w-full min-w-0 cursor-pointer appearance-none truncate pr-8 pl-2.5 text-[13px] disabled:cursor-not-allowed disabled:opacity-60 ${field}`}
      />
      <ChevronDown size={12} weight="bold" className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-ink-3" />
    </span>
  )
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`h-8 px-2.5 text-[13px] ${field} ${props.className ?? ''}`} />
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`w-full resize-y px-3 py-2.5 leading-5 ${field} ${props.className ?? ''}`} />
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: string; count?: number }[]
  onChange: (value: T) => void
}) {
  return (
    <div role="tablist" className="inline-flex gap-px rounded-[4px] bg-hover p-[2px] shadow-[inset_0_0_0_1px_var(--color-line)]">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={`h-7 rounded-[3px] px-2.5 text-[13px] font-medium transition-colors duration-150 ${
            o.value === value ? 'bg-page text-ink shadow-[0_0_0_1px_var(--color-control)]' : 'text-ink-2 hover:text-ink'
          }`}
        >
          {o.label}
          {o.count !== undefined && <span className="ml-1.5 font-mono text-[11px] text-ink-3">{o.count}</span>}
        </button>
      ))}
    </div>
  )
}

/* ---------------------------------------------------------------- cards */

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-[6px] bg-page p-5 shadow-card ${className}`}>
      {children}
    </section>
  )
}

export function CardHeader({ title, meta, right }: { title: ReactNode; meta?: ReactNode; right?: ReactNode }) {
  return (
    <header className="-mx-5 -mt-5 mb-4 flex min-h-11 items-center justify-between gap-4 border-b border-line px-5 py-2.5">
      <h2 className="text-[14px] font-semibold tracking-[-0.01em]">
        {title}
        {meta !== undefined && <span className="ml-2 font-mono text-[12px] font-normal text-ink-3">{meta}</span>}
      </h2>
      {right && <div className="flex items-center gap-2 text-[12.5px] text-ink-3">{right}</div>}
    </header>
  )
}

/** A status tag: square, hairline-bordered, with a marker in the tone's colour. */
export function Chip({ tone = 'idle', children }: { tone?: 'risk' | 'soon' | 'ok' | 'idle' | 'accent'; children: ReactNode }) {
  const t = {
    risk: 'text-risk-text bg-risk-soft/60 shadow-[inset_0_0_0_1px_rgba(196,43,49,0.22)]',
    soon: 'text-soon bg-soon-soft/60 shadow-[inset_0_0_0_1px_rgba(154,91,0,0.22)]',
    ok: 'text-ok-text bg-ok-soft/60 shadow-[inset_0_0_0_1px_rgba(15,122,95,0.22)]',
    idle: 'text-ink-2 bg-page shadow-[inset_0_0_0_1px_var(--color-control)]',
    accent: 'text-accent bg-accent-soft/60 shadow-[inset_0_0_0_1px_rgba(28,100,216,0.22)]',
  }[tone]
  const mark = { risk: 'bg-risk', soon: 'bg-soon-fill', ok: 'bg-ok', idle: 'bg-mark', accent: 'bg-accent-fill' }[tone]
  return (
    <span className={`inline-flex h-5 shrink-0 items-center gap-1.5 rounded-[2px] pr-1.5 pl-1.5 text-[11.5px] font-medium whitespace-nowrap ${t}`}>
      <span aria-hidden className={`size-[5px] shrink-0 rounded-[1px] ${mark}`} />
      {children}
    </span>
  )
}

/** Pill toggle, as in a date-range switch. */
export function Pills<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div role="tablist" className="flex gap-1">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={`h-7 rounded-[3px] px-2.5 text-[12.5px] font-medium transition-colors duration-150 ${
            o.value === value ? 'bg-ink text-on-ink' : 'text-ink-2 shadow-[inset_0_0_0_1px_var(--color-control)] hover:bg-hover'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Right-hand sheet over the page. */
export function Sheet({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true">
      <button aria-label="Close" onClick={onClose} className="absolute inset-0 cursor-default bg-[rgba(15,27,45,0.18)]" />
      <div className="relative flex h-full w-full max-w-[440px] flex-col overflow-y-auto bg-page p-6 shadow-[-8px_0_32px_rgba(15,27,45,0.12)]">
        {children}
      </div>
    </div>
  )
}

/** Centred dialog with a title, for short forms. Escape or the backdrop closes it. */
export function Modal({
  title,
  description,
  onClose,
  children,
  footer,
}: {
  title: ReactNode
  description?: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  // Portal: an ancestor with backdrop-filter would otherwise trap a fixed-position dialog.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <button aria-label="Close" onClick={onClose} className="absolute inset-0 cursor-default bg-[rgba(15,27,45,0.32)]" />
      <div className="relative flex max-h-[calc(100dvh-32px)] w-full max-w-[520px] flex-col overflow-hidden rounded-[8px] bg-page shadow-[0_24px_64px_rgba(15,27,45,0.24),0_0_0_1px_var(--color-line)]">
        <header className="border-b border-line px-6 pt-5 pb-4">
          <h2 id="modal-title" className="text-[16px] font-semibold tracking-[-0.01em]">
            {title}
          </h2>
          {description && <p className="mt-1 text-[14px] text-ink-2">{description}</p>}
        </header>
        <div className="overflow-y-auto px-6 py-5">{children}</div>
        {footer && <footer className="flex items-center justify-end gap-2 border-t border-line bg-app px-6 py-3.5">{footer}</footer>}
      </div>
    </div>,
    document.body,
  )
}
