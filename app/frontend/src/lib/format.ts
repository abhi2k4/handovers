const day = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
const dayShort = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })

export function date(ms?: number | null, short = false): string {
  if (!ms || ms >= 253402300799000) return ''
  return (short ? dayShort : day).format(new Date(ms))
}

export function pct(value?: number | null): string {
  if (!value) return ''
  return `${Math.round(value * 100)}%`
}

export function initials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function first(name?: string | null): string {
  return (name ?? '').split(' ')[0]
}

export function plural(n: number, word: string, many?: string): string {
  return `${n} ${n === 1 ? word : (many ?? `${word}s`)}`
}

export function daysBetween(from: number, to: number): number {
  return Math.max(0, Math.round((to - from) / 86_400_000))
}

export const CADENCE: Record<string, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  biweekly: 'Every two weeks',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  adhoc: 'As needed',
}

/** "just now", "5 min ago", "3 h ago", "2 days ago" relative to `now`. */
export function ago(ms: number, now: number): string {
  const min = Math.round((now - ms) / 60_000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min} min ago`
  const h = Math.round(min / 60)
  if (h < 24) return `${h} h ago`
  return plural(Math.round(h / 24), 'day') + ' ago'
}
