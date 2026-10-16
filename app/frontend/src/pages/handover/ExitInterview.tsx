import { useState } from 'react'
import { Button, Chip, TextArea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useViewAs } from '../../hooks/useViewAs'
import { api } from '../../lib/api'
import { first } from '../../lib/format'
import type { Fact, Gap, Handover } from '../../types/api'

interface Choice {
  id: string
  title: string | null
  value: string | null
}

interface Preview {
  facts: Fact[]
  note: string | null
  method: string
  /** "Sources disagree": the two claims, and which one the answer seems to name as current. */
  choices: Choice[] | null
  suggested: string | null
}

const ORDER: Record<string, number> = { G1: 0, G8: 1, G6: 2, M: 3, Q: 4, G7A: 5, G7S: 6, G2: 7, G4: 8 }

interface Powers {
  /** The leaver: answers. */
  answer: boolean
  /** HR or the manager: adds questions and follow-ups. */
  ask: boolean
  /** The manager: drops a question that does not apply (never a mandatory one). */
  dismiss: boolean
}

function Question({ gap, n, example, onSaved, can, hid }: { gap: Gap; n: number; example?: string; onSaved: () => void; can: Powers; hid: string }) {
  const [answer, setAnswer] = useState('')
  const [preview, setPreview] = useState<Preview | null>(null)
  const [keep, setKeep] = useState<string>('')
  const [followUp, setFollowUp] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const saved = gap.status === 'answered'

  async function review() {
    setBusy(true)
    setError(null)
    try {
      const p = await api.post<Preview>(`/gaps/${encodeURIComponent(gap.id)}/preview`, { answer })
      setPreview(p)
      setKeep(p.suggested ?? '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    if (!preview) return
    setBusy(true)
    try {
      await api.post(`/gaps/${encodeURIComponent(gap.id)}/confirm`, {
        answer,
        facts: preview.facts,
        ...(preview.choices?.length ? { keep } : {}),
      })
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
      setBusy(false)
    }
  }

  return (
    <li className="grid gap-x-6 border-b border-line py-7 md:grid-cols-[28px_minmax(0,1fr)]">
      <span className="num text-[14px] text-ink-3">{n}</span>
      <div className="max-w-[42rem]">
        <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[13px] text-ink-3">
          {saved ? <span className="text-ok-text">Answered · {gap.label}</span> : <span>{gap.label}</span>}
          {gap.mandatory && <Chip tone="accent">Required by policy</Chip>}
          {gap.context && gap.rule === 'Q' && <Chip>Follow-up</Chip>}
          {!saved && can.dismiss && !gap.mandatory && (
            <button onClick={() => void dismiss()} className="ml-auto text-ink-3 hover:text-risk-text hover:underline">
              Doesn't apply
            </button>
          )}
        </div>
        <p className="text-[16px] leading-6 font-medium tracking-[-0.005em]">{gap.question}</p>

        {saved ? (
          <p className="mt-3 border-l-2 border-line pl-3.5 text-[14px] leading-5 text-ink-2">
            {gap.answer?.split('\nA: ')[1] ?? gap.answer}
          </p>
        ) : preview ? (
          <div className="mt-4">
            <div className="rounded-[4px] bg-app px-4 py-3.5">
              <div className="mb-1.5 text-[13px] text-ink-3">What will be recorded</div>
              {preview.facts.length === 0 && <p className="text-[14px]">{preview.note}</p>}
              {preview.choices && preview.choices.length > 0 && (
                <fieldset className="mb-3 flex flex-col gap-1.5">
                  <legend className="mb-1.5 text-[13px] font-medium text-ink">Which one is current?</legend>
                  {[...preview.choices, { id: '', title: 'Neither, or I am not sure', value: null }].map((c) => (
                    <label key={c.id || 'none'} className={`flex cursor-pointer items-start gap-2.5 rounded-[4px] px-3 py-2 text-[14px] ${keep === c.id ? 'bg-page shadow-[inset_0_0_0_1px_var(--color-accent-fill)]' : 'hover:bg-page'}`}>
                      <input type="radio" name={`keep-${gap.id}`} checked={keep === c.id} onChange={() => setKeep(c.id)} className="mt-1 accent-[var(--color-accent-fill)]" />
                      <span>
                        {c.value && <span className="num font-semibold">{c.value}</span>}
                        <span className="block text-[13px] text-ink-2">{c.title}</span>
                      </span>
                    </label>
                  ))}
                  <span className="text-[12px] text-ink-3">Both claims stay in the graph. The other one is marked as replaced, with your answer as the reason.</span>
                </fieldset>
              )}
              {preview.facts.map((f) => (
                <div key={f.key} className="text-[14px] leading-5">
                  <div className="font-medium">{f.title}</div>
                  {f.rationale && <p className="mt-1 text-ink-2">{f.rationale}</p>}
                  {f.steps && f.steps.length > 0 && (
                    <ol className="mt-1 list-decimal pl-4 text-ink-2">
                      {f.steps.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ol>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <Button onClick={save} disabled={busy}>
                {busy ? 'Saving…' : 'Save'}
              </Button>
              <Button variant="ghost" onClick={() => setPreview(null)} disabled={busy}>
                Edit answer
              </Button>
            </div>
          </div>
        ) : !can.answer ? (
          <p className="mt-3 text-[13px] text-ink-3">Waiting for the answer.</p>
        ) : (
          <div className="mt-4">
            <TextArea rows={3} placeholder="Answer in your own words" value={answer} onChange={(e) => setAnswer(e.target.value)} />
            <div className="mt-2.5 flex items-center gap-3">
              <Button onClick={review} disabled={busy || answer.trim().length < 3}>
                {busy ? 'Reading…' : 'Review'}
              </Button>
              {example && !answer && (
                <Button variant="link" onClick={() => setAnswer(example)}>
                  Use the sample answer
                </Button>
              )}
            </div>
          </div>
        )}
        {saved && can.ask && followUp === null && (
          <button onClick={() => setFollowUp('')} className="mt-2 text-[13px] text-accent hover:underline">
            Ask a follow-up
          </button>
        )}
        {followUp !== null && (
          <AskBox hid={hid} follows={gap.id} initial={followUp} onDone={() => { setFollowUp(null); onSaved() }} onCancel={() => setFollowUp(null)} />
        )}
        {error && <p className="mt-3 text-[13px] text-risk-text">{error}</p>}
      </div>
    </li>
  )

  async function dismiss() {
    const reason = window.prompt('Why does this question not apply? (kept in the audit trail)')
    if (reason === null) return
    try {
      await api.post(`/gaps/${encodeURIComponent(gap.id)}/dismiss`, { reason })
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }
}

/** HR or the manager adds a question (or a follow-up). The leaver is told. */
function AskBox({ hid, follows, initial = '', onDone, onCancel }: { hid: string; follows?: string; initial?: string; onDone: () => void; onCancel?: () => void }) {
  const [text, setText] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function ask() {
    setBusy(true)
    setError('')
    try {
      await api.post(`/handovers/${encodeURIComponent(hid)}/questions`, { question: text, follows: follows ?? null })
      setText('')
      onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="mt-3 flex flex-col gap-2">
      <TextArea rows={2} placeholder={follows ? 'What would you like them to clarify?' : 'For example: which agency invoices are still unpaid?'} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex items-center gap-2">
        <Button variant="secondary" onClick={ask} disabled={busy || text.trim().length < 8}>
          {busy ? 'Adding…' : follows ? 'Send follow-up' : 'Add question'}
        </Button>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
        {error && <span className="text-[13px] text-risk-text">{error}</span>}
      </div>
    </div>
  )
}

export function ExitInterview({ h, onChange }: { h: Handover; onChange: () => void }) {
  const { data: examples } = useApi<Record<string, string>>('/demo/answers')
  const sort = (a: Gap, b: Gap) => (ORDER[a.rule] ?? 9) - (ORDER[b.rule] ?? 9) || b.priority - a.priority
  const questions = h.gaps.filter((g) => g.interview).sort(sort)
  const extra = h.gaps.filter((g) => g.extra).sort(sort)
  const answered = questions.filter((q) => q.status === 'answered').length
  const name = first(h.employee)
  const { me } = useViewAs()
  const self = me?.id === h.employee_id
  const can: Powers = { answer: h.can?.answer ?? self, ask: h.can?.ask ?? false, dismiss: h.can?.dismiss ?? false }
  const [showExtra, setShowExtra] = useState(answered === questions.length && questions.length > 0)
  const [asking, setAsking] = useState(false)
  const departed = h.employee_status === 'departed'

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <p className="max-w-[40rem] text-[16px] leading-6 text-ink-2">
          Only what nothing else explains, plus the questions company policy asks every leaver. {self ? 'You see' : `${name} sees`} exactly what will be
          recorded before anything is saved.{' '}
          <span className="num text-ink">
            {answered} of {questions.length}
          </span>{' '}
          answered.
        </p>
        {can.ask && !departed && h.status !== 'cancelled' && !asking && (
          <Button variant="secondary" onClick={() => setAsking(true)}>
            Ask {name} a question
          </Button>
        )}
      </div>
      {asking && (
        <div className="mb-6 rounded-[6px] bg-app p-4">
          <div className="text-[14px] font-medium">A question for {name}</div>
          <p className="text-[13px] text-ink-3">It joins the required questions, and {name} is notified.</p>
          <AskBox hid={h.id} onDone={() => { setAsking(false); onChange() }} onCancel={() => setAsking(false)} />
        </div>
      )}
      <ol className="border-t border-line">
        {questions.map((g, i) => (
          <Question key={g.id} gap={g} n={i + 1} example={examples?.[g.target_id] ?? examples?.[g.question]} onSaved={onChange} can={can} hid={h.id} />
        ))}
      </ol>
      {extra.length > 0 && (
        <section className="mt-10">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h3 className="text-[16px] font-semibold">
              More to capture <span className="num font-normal text-ink-3">{extra.filter((g) => g.status === 'open').length}</span>
            </h3>
            <button onClick={() => setShowExtra((v) => !v)} className="text-[13px] text-accent hover:underline">
              {showExtra ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="mt-1 max-w-[40rem] text-[14px] text-ink-3">
            Not required for the last day. Every answer here is one less thing {h.successor ? first(h.successor) : 'the successor'} has to rediscover.
          </p>
          {showExtra && (
            <ol className="mt-4 border-t border-line">
              {extra.map((g, i) => (
                <Question key={g.id} gap={g} n={questions.length + i + 1} example={examples?.[g.target_id] ?? examples?.[g.question]} onSaved={onChange} can={can} hid={h.id} />
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  )
}
