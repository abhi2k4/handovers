import { useState } from 'react'
import { Plus, X } from '../components/icons'
import { Button, Card, CardHeader, Chip, ErrorNote, Input, PageHeader, PageSkeleton, Select, TextArea } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { ago, date } from '../lib/format'

interface Policy {
  version: number
  can_edit: boolean
  withdrawal_days: number
  letter_on_last_day: boolean
  mandatory_questions: string[]
  hr_teams: string[]
  hr_is_it: boolean
  exec_titles: string[]
  role_groups: Record<string, string>
  timezone: string
  country_code: string
  digest_hour: number
}

interface Job {
  id: string
  kind: string
  label: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  run_at: number
  attempts: number
  handover: string
  finished_at: number | null
  last_error: string | null
  result: Record<string, unknown> | null
}

interface Meta {
  now: number
}

const ZONES = ['Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Los_Angeles', 'Australia/Sydney', 'UTC']
const ROLE_LABEL: Record<string, string> = { hr: 'HR', it: 'IT', exec: 'Leadership' }
const STATUS_TONE: Record<Job['status'], 'ok' | 'risk' | 'soon' | 'idle' | 'accent'> = { done: 'ok', failed: 'risk', queued: 'accent', running: 'soon', cancelled: 'idle' }

const list = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean)

/** The company's exit policy (HR, or the Handovers team during onboarding), and the job queue. */
export function PolicyPage() {
  const { data, error, reload } = useApi<Policy>('/policy')
  // Edits live in a draft over the saved policy; saving clears it and reloads.
  const [draft, setP] = useState<Policy | null>(null)
  const p = draft ?? data
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  if (error) return <ErrorNote message={error} />
  if (!p) return <PageSkeleton />
  const edit = p.can_edit
  const set = (patch: Partial<Policy>) => setP({ ...p, ...patch })

  async function save() {
    if (!p) return
    setSaving(true)
    setMsg(null)
    try {
      await api.put('/policy', p)
      setMsg({ ok: true, text: 'Saved. New handovers use it now; open ones keep their questions.' })
      setP(null)
      reload()
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : 'Failed' })
    } finally {
      setSaving(false)
    }
  }

  const groups = Object.entries(p.role_groups)
  return (
    <>
      <PageHeader
        title="Policies"
        sub="How your company runs exits. Set once during onboarding, then adjust as policies change. Every change is versioned."
        right={
          <span className="flex items-center gap-3">
            <Chip>Version {p.version}</Chip>
            {edit && (
              <Button onClick={() => void save()} disabled={saving}>
                {saving ? 'Saving…' : 'Save policy'}
              </Button>
            )}
          </span>
        }
      />
      {msg && <p className={`mb-4 text-[14px] ${msg.ok ? 'text-ok-text' : 'text-risk-text'}`}>{msg.text}</p>}

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <Card>
            <CardHeader title="Resignation and exit" />
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-[14px]">
                <span className="font-medium">Withdrawal window</span>
                <span className="flex items-center gap-2">
                  <Input type="number" min={0} max={90} value={p.withdrawal_days} disabled={!edit} onChange={(e) => set({ withdrawal_days: Number(e.target.value) })} className="w-24" />
                  <span className="text-ink-3">days after the resignation</span>
                </span>
                <span className="text-[13px] text-ink-3">A handover can be cancelled within this window, never after the transfer is approved.</span>
              </label>
              <label className="flex items-start gap-2.5 text-[14px]">
                <input type="checkbox" checked={p.letter_on_last_day} disabled={!edit} onChange={(e) => set({ letter_on_last_day: e.target.checked })} className="mt-1 accent-[var(--color-accent-fill)]" />
                <span>
                  <span className="block font-medium">Relieving letter on the last day</span>
                  <span className="text-[13px] text-ink-3">HR can prepare it early and schedule it; it is only sent from the last day.</span>
                </span>
              </label>
            </div>
          </Card>

          <Card>
            <CardHeader title="Questions every leaver answers" meta={p.mandatory_questions.length} />
            <p className="-mt-2 mb-3 text-[14px] text-ink-3">Added to every exit interview, on top of what the graph finds. They can't be dropped.</p>
            <ol className="flex flex-col gap-2">
              {p.mandatory_questions.map((q, i) => (
                <li key={i} className="grid grid-cols-[20px_minmax(0,1fr)_auto] items-start gap-2">
                  <span className="num pt-2 text-[13px] text-ink-3">{i + 1}</span>
                  <TextArea rows={2} value={q} disabled={!edit} onChange={(e) => set({ mandatory_questions: p.mandatory_questions.map((x, n) => (n === i ? e.target.value : x)) })} />
                  {edit && (
                    <button aria-label="Remove question" onClick={() => set({ mandatory_questions: p.mandatory_questions.filter((_, n) => n !== i) })} className="mt-1.5 rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-risk-text">
                      <X size={15} />
                    </button>
                  )}
                </li>
              ))}
            </ol>
            {edit && (
              <Button variant="ghost" className="mt-2" onClick={() => set({ mandatory_questions: [...p.mandatory_questions, ''] })}>
                <Plus size={14} /> Add a question
              </Button>
            )}
          </Card>

          <Card>
            <CardHeader title="Who is who" />
            <p className="-mt-2 mb-4 text-[14px] text-ink-3">
              Roles come from your directory and sign-in groups (synced from Microsoft Entra ID, Google Workspace or your SSO), so nobody maintains a second list.
            </p>
            <div className="flex flex-col gap-4 text-[14px]">
              <label className="flex flex-col gap-1.5">
                <span className="font-medium">HR teams or departments</span>
                <Input value={p.hr_teams.join(', ')} disabled={!edit} onChange={(e) => set({ hr_teams: list(e.target.value) })} />
                <span className="text-[13px] text-ink-3">Team ids or department names, comma-separated. People in these run handovers.</span>
              </label>
              <label className="flex items-center gap-2.5">
                <input type="checkbox" checked={p.hr_is_it} disabled={!edit} onChange={(e) => set({ hr_is_it: e.target.checked })} className="accent-[var(--color-accent-fill)]" />
                <span>HR also administers accounts (no separate IT team)</span>
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="font-medium">Leadership titles</span>
                <Input value={p.exec_titles.join(', ')} disabled={!edit} onChange={(e) => set({ exec_titles: list(e.target.value) })} />
              </label>
              <div className="flex flex-col gap-1.5">
                <span className="font-medium">Sign-in groups</span>
                {groups.length === 0 && <span className="text-[13px] text-ink-3">No groups mapped yet.</span>}
                {groups.map(([g, role], i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={g}
                      disabled={!edit}
                      placeholder="Group name, e.g. IT Admins"
                      className="min-w-0 flex-1"
                      onChange={(e) => set({ role_groups: Object.fromEntries(groups.map(([k, v], n) => (n === i ? [e.target.value, v] : [k, v]))) })}
                    />
                    <Select value={role} disabled={!edit} onChange={(e) => set({ role_groups: Object.fromEntries(groups.map(([k, v], n) => (n === i ? [k, e.target.value] : [k, v]))) })}>
                      {Object.entries(ROLE_LABEL).map(([v, l]) => (
                        <option key={v} value={v}>
                          {l}
                        </option>
                      ))}
                    </Select>
                    {edit && (
                      <button aria-label="Remove group" onClick={() => set({ role_groups: Object.fromEntries(groups.filter((_, n) => n !== i)) })} className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-risk-text">
                        <X size={15} />
                      </button>
                    )}
                  </div>
                ))}
                {edit && (
                  <Button variant="ghost" className="self-start" onClick={() => set({ role_groups: { ...p.role_groups, '': 'hr' } })} disabled={'' in p.role_groups}>
                    <Plus size={14} /> Map a group
                  </Button>
                )}
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Region" />
            <div className="grid gap-4 text-[14px] sm:grid-cols-3">
              <label className="flex flex-col gap-1.5">
                <span className="font-medium">Time zone</span>
                <Select value={p.timezone} disabled={!edit} onChange={(e) => set({ timezone: e.target.value })}>
                  {[...new Set([p.timezone, ...ZONES])].map((z) => (
                    <option key={z} value={z}>
                      {z}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="font-medium">Phone country code</span>
                <Input value={p.country_code} disabled={!edit} onChange={(e) => set({ country_code: e.target.value.replace(/\D/g, '') })} />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="font-medium">Daily summary at</span>
                <Select value={p.digest_hour} disabled={!edit} onChange={(e) => set({ digest_hour: Number(e.target.value) })}>
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>
                      {String(h).padStart(2, '0')}:00
                    </option>
                  ))}
                </Select>
              </label>
            </div>
            <p className="mt-3 text-[13px] text-ink-3">Quiet hours, the daily summary and dates on letters use this time zone.</p>
          </Card>
        </div>

        <aside className="flex min-w-0 flex-col gap-4">
          <Jobs />
        </aside>
      </div>
    </>
  )
}

/** The background job queue: what runs on its own, when, and what happened. */
function Jobs() {
  const { data: jobs, reload } = useApi<Job[]>('/jobs')
  const { data: meta } = useApi<Meta>('/meta')
  const [busy, setBusy] = useState('')
  const now = meta?.now ?? 0

  async function run(id: string) {
    setBusy(id)
    try {
      await api.post(`/jobs/${encodeURIComponent(id)}/run`)
      reload()
    } finally {
      setBusy('')
    }
  }

  const upcoming = (jobs ?? []).filter((j) => j.status === 'queued').sort((a, b) => a.run_at - b.run_at)
  const past = (jobs ?? []).filter((j) => j.status !== 'queued').slice(0, 8)
  return (
    <Card>
      <CardHeader title="Background jobs" meta={upcoming.length || undefined} right="Runs on its own" />
      <p className="-mt-2 mb-3 text-[14px] text-ink-3">The daily summary, last-day warnings, alerts held over quiet hours, departures and letters. Run one now to see it.</p>
      <ul className="flex flex-col divide-y divide-line">
        {upcoming.map((j) => (
          <li key={j.id} className="flex items-center justify-between gap-3 py-2">
            <span className="min-w-0">
              <span className="block truncate text-[14px]">{j.label}</span>
              <span className="num block text-[12px] text-ink-3">{date(j.run_at, true)}{j.attempts ? ` · try ${j.attempts + 1}` : ''}</span>
            </span>
            <Button variant="ghost" className="h-8 text-[13px]" onClick={() => void run(j.id)} disabled={busy === j.id}>
              {busy === j.id ? 'Running…' : 'Run now'}
            </Button>
          </li>
        ))}
      </ul>
      {past.length > 0 && (
        <>
          <div className="mt-4 mb-1 text-[13px] font-medium text-ink-3">Recent</div>
          <ul className="flex flex-col divide-y divide-line">
            {past.map((j) => (
              <li key={j.id} className="flex items-center justify-between gap-3 py-2">
                <span className="min-w-0">
                  <span className="block truncate text-[14px]">{j.label}</span>
                  <span className="block truncate text-[12px] text-ink-3">
                    {j.finished_at && now ? ago(j.finished_at, now) : ''}
                    {j.last_error ? ` · ${j.last_error}` : j.result ? ` · ${Object.entries(j.result).map(([k, v]) => `${k.replace('_', ' ')} ${String(v)}`).join(', ')}` : ''}
                  </span>
                </span>
                <Chip tone={STATUS_TONE[j.status]}>{j.status}</Chip>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  )
}
