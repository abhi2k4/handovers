import type { Stage } from '../components/Pipeline'

/** Shared by the HR overview and the leadership home: who holds what alone, and how handovers stand. */

export type Kind = 'responsibilities' | 'accounts' | 'relationships' | 'knowledge'

export interface RiskPerson {
  id: string
  name: string
  title: string
  team: string
  risk: number
  sole: Partial<Record<Kind, number>>
  leaving: boolean
}

export interface DashHandover {
  id: string
  status: string
  employee_id: string
  employee: string
  title: string
  successor: string | null
  successor_id: string | null
  effective_at: number
  days_left: number
  notice_days: number | null
  questions: number
  answered: number
  open_access: number
  ready: boolean
  stages: Stage[]
  /** The same last-day checks as the handover page (GET /handovers/{id}/readiness). */
  steps: { key: string; label: string; done: boolean; href: string }[]
}

export const KINDS: { key: Kind; label: string; color: string }[] = [
  { key: 'responsibilities', label: 'Work', color: 'var(--color-c1)' },
  { key: 'accounts', label: 'Accounts', color: 'var(--color-c2)' },
  { key: 'relationships', label: 'Contacts', color: 'var(--color-c3)' },
  { key: 'knowledge', label: 'Knowledge', color: 'var(--color-c4)' },
]

export function health(h: DashHandover): { tone: 'risk' | 'soon' | 'ok' | 'idle'; label: string } {
  if (h.status === 'transferred') return { tone: 'idle', label: 'Handed over' }
  const remaining = h.questions - h.answered
  if (h.ready) return { tone: 'ok', label: 'Ready' }
  if (h.days_left <= 7 && (remaining > 0 || h.open_access > 0)) return { tone: 'risk', label: 'Off track' }
  if (h.open_access > 0 || !h.successor_id) return { tone: 'soon', label: 'At risk' }
  return { tone: 'ok', label: 'On track' }
}
