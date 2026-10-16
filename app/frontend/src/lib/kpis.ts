import type { DashHandover, Kind, RiskPerson } from './orgRisk'
import type { Figure } from '../components/StatBand'
import { AlertTriangle, ArrowRightLeft, ChatCircleDots, CheckCircle2, KeyRound, Lifebuoy, Brain, ShieldWarning, Target, Timer, UserRound } from '../components/icons'

/** GET /api/kpis: every number is measured from the graph (app/backend/services/kpis.py). */

export interface Kpi {
  key: string
  label: string
  value: number | null
  unit: string
  target: number | null
  detail: string
}

export interface Kpis {
  now: number
  company: string
  headcount: { active: number; leaving: number; joining: number; departed: number }
  process: Kpi[]
  risk: Kpi[]
  risk_by_kind: Record<Kind, number>
  teams: { id: string; name: string; total: number; sole: number; coverage: number | null }[]
  people: RiskPerson[]
  handovers: (DashHandover & { gaps: number; open_gaps: number })[]
  /** Over completed handovers; `value` is null until one completes. */
  outcomes: Kpi[]
}

export function show(k: Kpi): string {
  return k.value === null ? '–' : `${k.value}${k.unit === '%' ? '%' : ''}`
}

/** Higher is better for percentages with a target; for counts with target 0, lower is better. */
export function tone(k: Kpi): 'risk' | 'soon' | 'ok' | undefined {
  if (k.value === null || k.target === null) return undefined
  if (k.target === 0) return k.value === 0 ? 'ok' : 'risk'
  if (k.value >= k.target) return 'ok'
  return k.value < k.target / 2 ? 'risk' : 'soon'
}

const TONE_CLASS = { risk: 'text-risk-text', soon: 'text-soon', ok: 'text-ok-text' } as const

const ICON: Record<string, Figure['icon']> = {
  north_star: Target,
  accounts_reassigned: KeyRound,
  exit_capture: ChatCircleDots,
  handovers_completed: ArrowRightLeft,
  backup_coverage: Lifebuoy,
  held_by_one: UserRound,
  unexplained: ShieldWarning,
  contradictions: AlertTriangle,
  on_time: Timer,
  knowledge_passed: Brain,
  exit_answers: ChatCircleDots,
  accounts_closed: CheckCircle2,
}

/** A KPI as a tile: percentages get a meter (with a tick when the target is below 100%). */
export function figure(k: Kpi): Figure {
  const t = tone(k)
  return {
    label: k.label,
    value: show(k),
    note: k.detail,
    tone: t ? TONE_CLASS[t] : undefined,
    icon: ICON[k.key],
    meter: k.unit === '%' && k.value !== null ? { value: k.value, max: 100, target: k.target !== null && k.target < 100 ? k.target : null } : undefined,
  }
}
