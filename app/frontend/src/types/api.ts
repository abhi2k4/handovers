// Response shapes of the Handovers API (app/backend/api/*.py).

export interface PersonRow {
  id: string
  name: string
  title: string
  status: 'active' | 'incoming' | 'departed'
  team: string
  team_id: string
  manager: string | null
  handover_id: string | null
  handover_status: string | null
  risk: number
  sole: Partial<Record<'responsibilities' | 'accounts' | 'relationships' | 'knowledge', number>>
}

export interface Responsibility {
  id: string
  title: string
  cadence: string | null
  since: number
  last_seen: number | null
  via: string
  co_owners: string[]
  evidence: number
  eods: number
  share: number
  skills: string[]
  next_due: number | null
  overdue: boolean
}

export interface Account {
  id: string
  name: string
  system: string
  role: string
  other_admins: string[]
}

export interface Stakeholder {
  id: string
  name: string
  org: string
  kind: string
  context: string | null
  touches: number
  other_contacts: string[]
}

export interface Knowledge {
  id: string
  kind: 'Decision' | 'Procedure' | 'Claim'
  title: string
  rationale: string | null
  value: string | null
  steps: string[] | null
  status: string
  valid_from: number
  valid_to: number
  confidence: number
  sources: number
  sensitivity: string
  private: boolean
  via: string
  others: string[]
  documented: boolean
  justified_by: string | null
}

export interface Person {
  id: string
  name: string
  title: string
  email: string
  status: string
  joined_at: number
  team: string
  team_id: string
  role: string
  manager: string | null
  manager_id: string | null
  sources: number
  eod_total: number
  responsibilities: Responsibility[]
  accounts: Account[]
  stakeholders: Stakeholder[]
  knowledge: Knowledge[]
  skills: { id: string; name: string; category: string; evidence: number }[]
  open_work: { id: string; title: string; opened: number }[]
  recent: { id: string; kind: string; title: string; at: number; sensitivity: string }[]
}

export interface Gap {
  id: string
  rule: string
  label: string
  target_id: string
  target_kind: string
  title: string
  question: string
  priority: number
  status: 'open' | 'answered' | 'dismissed'
  answer: string | null
  /** One of the questions readiness waits on (mandatory, asked, top found). */
  interview: boolean
  /** More questions the graph found, for the days left once the required ones are answered. */
  extra?: boolean
  mandatory?: boolean
  asked_by?: string | null
  resolution?: string | null
  context?: string | null
  /** HR's copy: knowledge items keep only their label (services/access.py redact_gaps). */
  redacted?: boolean
}

export interface Approver {
  id: string | null
  name: string | null
  via: 'manager' | 'skip-level manager' | 'hr'
}

export interface Handover {
  id: string
  status: string
  created_at: number
  effective_at: number
  notice_days: number
  employee_id: string
  employee: string
  title: string
  team: string
  manager_id: string | null
  manager: string | null
  successor_id: string | null
  successor: string | null
  successor_title: string | null
  gaps: Gap[]
  transfer: {
    id: string
    status: string
    decision: 'approved' | 'rejected' | null
    comment: string | null
    approved_by: string | null
    approved_at: number | null
    included: number
    excluded: number
  } | null
  team_id?: string | null
  employee_status?: string
  cancelled_at?: number | null
  cancel_reason?: string | null
  letter_sent_at?: number | null
  approver?: Approver
  cancel?: { allowed: boolean; until: number | null; reason: string }
  can?: { run: boolean; approve: boolean; ask: boolean; dismiss: boolean; answer: boolean; notes: boolean }
  redacted?: boolean
}

export interface HandoverRow {
  id: string
  status: string
  created_at: number
  effective_at: number
  employee_id: string
  employee: string
  title: string
  successor: string | null
  gaps: number
  open_gaps: number
}

export interface JobDescription {
  title: string
  role: string
  team: string
  reports_to: string | null
  summary: string
  responsibilities: { id: string; text: string; cadence: string | null; share: number; evidence: number; sole: boolean; with: string[] }[]
  must: { id: string; name: string; evidence: number }[]
  nice: { id: string; name: string; evidence: number }[]
  tools: string[]
  stakeholders: { id: string; name: string; org: string; context: string }[]
  accounts: { id: string; name: string; role: string }[]
  evidence_total: number
  diff: { old_title: string | null; missing: { id: string; title: string }[]; unused: string[] }
  model: string
}

export interface Criterion {
  id: string
  label: string
  level: 'must' | 'nice'
  why: string
  signals: string[]
}

export interface Verdict {
  id: string
  label: string
  level: 'must' | 'nice'
  verdict: 'meets' | 'unclear' | 'missing'
  quote: string | null
  ask: string | null
}

export interface InterviewKit {
  questions: { id: string; skill: string; question: string; listen_for: string[]; red_flags: string[]; context: string }[]
  model: string
}

export interface PlanItem {
  id: string
  title: string
  detail: string
  receiver?: { id: string; name: string; why: string } | null
  due?: number | null
  overdue?: boolean
  urgent: boolean
  status?: string
}

export interface Plan {
  sections: { key: string; title: string; items: PlanItem[] }[]
}

export interface Fact {
  kind: string
  key: string
  title: string
  rationale?: string
  steps?: string[]
}

export interface Citation {
  id: string
  kind: string
  title: string
  via: string | null
  from: string | null
  approved_by: string | null
  approved_at: number | null
  decision: string | null
  previous: string | null
  valid_from: number | null
  evidence: { id: string; kind: string; title: string; at: number; author?: string; quote?: string }[]
}

export interface Answer {
  status: 'answered' | 'abstained'
  answer: string
  citations: Citation[]
  ask: { id: string; name: string; title: string }[]
  method: string
}
