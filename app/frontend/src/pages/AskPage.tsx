import { ArrowUp } from '../components/icons'
import type { ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { Avatar, Chip, Select } from '../components/ui'
import { useViewAs } from '../hooks/useViewAs'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { date, first } from '../lib/format'
import type { Answer, Citation, PersonRow } from '../types/api'

interface Turn {
  question: string
  answer?: Answer
  error?: string
}

const SOURCE_LABEL: Record<string, string> = { InterviewAnswer: 'Exit interview', EOD: 'Daily report' }

/** One stop on the path an answer took through the graph. */
function Stop({ tone, children }: { tone: 'source' | 'person' | 'approval' | 'you'; children: ReactNode }) {
  const dot = { source: 'bg-mark', person: 'bg-accent-fill', approval: 'bg-ok', you: 'bg-ink' }[tone]
  return (
    <span className="inline-flex h-6 items-center gap-1.5 rounded-[2px] bg-page px-2 text-[11.5px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)]">
      <span className={`size-[5px] rounded-[1px] ${dot}`} aria-hidden />
      {children}
    </span>
  )
}

/**
 * "How we know": the path from the original sources, through the person who knew it and the manager
 * who approved the transfer, to the asker. Every stop is a node or edge in the graph.
 */
function Trail({ c, you, onSources }: { c: Citation; you: string; onSources: () => void }) {
  const kinds = [...new Set(c.evidence.map((e) => SOURCE_LABEL[e.kind] ?? e.kind))]
  const link = <span className="h-px w-3 shrink-0 bg-strong" aria-hidden />
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1" aria-label="How we know">
      {c.evidence.length > 0 && (
        <>
          <button onClick={onSources} className="rounded-[2px] hover:opacity-80">
            <Stop tone="source">
              {kinds.slice(0, 2).join(', ')}
              {c.evidence.length > 1 ? ` (${c.evidence.length})` : ''}
            </Stop>
          </button>
          {link}
        </>
      )}
      {c.via === 'transfer' ? (
        <>
          <Stop tone="person">{c.from}</Stop>
          {link}
          {c.approved_by && (
            <>
              <Stop tone="approval">
                Approved by {c.approved_by}
                {c.approved_at ? `, ${date(c.approved_at, true)}` : ''}
              </Stop>
              {link}
            </>
          )}
        </>
      ) : null}
      <Stop tone="you">{c.via === 'transfer' ? you : `${you}'s own work`}</Stop>
    </div>
  )
}

function Provenance({ c, you }: { c: Citation; you: string }) {
  const [open, setOpen] = useState(false)
  return (
    <li className="border-t border-line py-2.5 text-[13px]">
      <div className="flex items-baseline gap-3">
        <span className="eyebrow w-[92px] shrink-0 pt-0.5">{c.kind}</span>
        <div className="min-w-0 flex-1">
          <div className="text-[14px] leading-5 text-ink">{c.title}</div>
          {(c.valid_from || c.previous) && (
            <div className="text-ink-3">
              {c.valid_from ? `True since ${date(c.valid_from, true)}` : ''}
              {c.valid_from && c.previous ? ', ' : ''}
              {c.previous ? `was ${c.previous}` : ''}
            </div>
          )}
          <Trail c={c} you={you} onSources={() => setOpen((o) => !o)} />
          {open && (
            <ul className="mt-2 flex flex-col gap-1.5">
              {c.evidence.map((e) => (
                <li key={e.id} className="text-ink-2">
                  {e.kind === 'InterviewAnswer' ? 'Exit interview' : e.title}
                  <span className="text-ink-3">
                    {e.author ? ` · ${e.author}` : ''}
                    {e.at ? ` · ${date(e.at, true)}` : ''}
                  </span>
                  {e.quote && e.kind !== 'InterviewAnswer' && <div className="text-ink-3">“{e.quote}”</div>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </li>
  )
}

interface Profile {
  id: string
  name: string
  title: string | null
  team: string | null
  counts: { knowledge: number; work: number; people: number; accounts: number }
  only_you: number
  inherited: number
  suggestions: string[]
  model: string
}

/** An answer's text: plain sentences, or "- " lines shown as a list. */
function AnswerText({ text, muted }: { text: string; muted: boolean }) {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
  const intro = lines.filter((l) => !l.startsWith('- '))
  const items = lines.filter((l) => l.startsWith('- ')).map((l) => l.slice(2))
  return (
    <div className={`text-[15px] leading-6 ${muted ? 'text-ink-2' : 'text-ink'}`}>
      {intro.map((l) => (
        <p key={l} className="mb-2 last:mb-0">
          {l}
        </p>
      ))}
      {items.length > 0 && (
        <ul className="mt-1 flex flex-col gap-1.5">
          {items.map((l) => (
            <li key={l} className="grid grid-cols-[10px_minmax(0,1fr)] gap-2">
              <span aria-hidden className="mt-[9px] size-[5px] rounded-[1px] bg-accent-fill" />
              <span>{l}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Whose memory this is and what it holds: the only place answers can come from. */
function MemoryPanel({ p, onAsk }: { p: Profile; onAsk: (q: string) => void }) {
  const figures: [string, number][] = [
    ['Knowledge', p.counts.knowledge],
    ['Work', p.counts.work],
    ['People', p.counts.people],
    ['Accounts', p.counts.accounts],
  ]
  const total = figures.reduce((n, [, v]) => n + v, 0)
  return (
    <aside className="flex flex-col gap-4 lg:sticky lg:top-[88px] lg:self-start">
      <section className="rounded-[6px] bg-page shadow-card">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <Avatar name={p.name} size={32} />
          <span className="min-w-0">
            <span className="block truncate text-[14px] font-semibold">{p.name}</span>
            <span className="block truncate text-[12.5px] text-ink-3">{[p.title, p.team].filter(Boolean).join(' · ')}</span>
          </span>
        </div>
        <div className="grid grid-cols-4 divide-x divide-line border-b border-line">
          {figures.map(([label, v]) => (
            <div key={label} className="px-3 py-2.5">
              <div className="eyebrow">{label}</div>
              <div className={`num mt-0.5 text-[18px] font-semibold ${v ? 'text-ink' : 'text-strong'}`}>{v}</div>
            </div>
          ))}
        </div>
        <div className="px-4 py-3 text-[12.5px] leading-5 text-ink-2">
          {total === 0 ? (
            <>Nothing here yet. A successor's memory fills when the transfer is approved; until then the assistant says it doesn't know.</>
          ) : (
            <>
              <span className="num font-medium text-ink">{p.only_you}</span> held by no one else
              {p.inherited ? (
                <>
                  {' '}
                  · <span className="num font-medium text-ink">{p.inherited}</span> handed over
                </>
              ) : null}
              .
            </>
          )}
        </div>
      </section>
      {p.suggestions.length > 0 && (
        <section>
          <div className="eyebrow mb-2">Try asking</div>
          <ul className="flex flex-col gap-1">
            {p.suggestions.map((q) => (
              <li key={q}>
                <button
                  onClick={() => onAsk(q)}
                  className="w-full rounded-[4px] px-2.5 py-1.5 text-left text-[13px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)] transition-colors hover:bg-app hover:text-ink"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="font-mono text-[10.5px] leading-4 text-ink-3">
        {p.model === 'none' ? 'Answers composed from the graph, no model.' : `Phrased by ${p.model}. Every answer cites items from this memory; anything else is refused.`}
      </p>
    </aside>
  )
}

/** The sources behind an answer: the first three, the rest on request. */
function Sources({ citations, you }: { citations: Citation[]; you: string }) {
  const [all, setAll] = useState(false)
  const shown = all ? citations : citations.slice(0, 3)
  return (
    <>
      <ul className="mt-4">
        {shown.map((c) => (
          <Provenance key={c.id} c={c} you={you} />
        ))}
      </ul>
      {citations.length > shown.length && (
        <button onClick={() => setAll(true)} className="mt-1 font-mono text-[11px] text-accent hover:underline">
          + {citations.length - shown.length} more sources
        </button>
      )}
    </>
  )
}

export function AskPage() {
  const [params] = useSearchParams()
  const { persona } = useViewAs()
  // Signed in or viewing as someone: ask your own memory by default.
  return <Ask key={params.get('as') ?? persona} fallback={persona} />
}

function Ask({ fallback }: { fallback: string }) {
  const [params, setParams] = useSearchParams()
  const { persona } = useViewAs()
  const { data: people } = useApi<PersonRow[]>(persona ? null : '/people')
  const as = params.get('as') ?? fallback
  const { data: profile } = useApi<Profile>(as ? `/companion/${encodeURIComponent(as)}/profile` : null)
  const [turns, setTurns] = useState<Turn[]>([])
  // `?q=` pre-fills a question, e.g. "Ask how" on a ramp-up plan item.
  const [question, setQuestion] = useState(params.get('q') ?? '')
  const [busy, setBusy] = useState(false)
  // One conversation per visit, so follow-ups ("and why?") lean on this visit's questions only.
  const [session] = useState(() => `ses:${as}:${Math.random().toString(36).slice(2, 10)}`)
  const endRef = useRef<HTMLDivElement>(null)
  const name = first(profile?.name ?? people?.find((p) => p.id === as)?.name)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns])

  async function ask(q: string) {
    if (!q.trim() || !as) return
    setQuestion('')
    setBusy(true)
    setTurns((t) => [...t, { question: q }])
    try {
      const answer = await api.post<Answer>(`/companion/${encodeURIComponent(as)}/ask`, { question: q, session })
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, answer } : x)))
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: e instanceof Error ? e.message : 'Failed' } : x)))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-[1080px] grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="flex min-h-[calc(100dvh-220px)] min-w-0 flex-col md:min-h-[calc(100dvh-170px)]">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-[24px] leading-8 font-semibold tracking-[-0.025em]">Ask</h1>
            <p className="mt-1 text-[14px] text-ink-2">{as ? `Answers only from ${persona === as ? 'your' : `${name}’s`} work memory, with the source of every fact.` : 'Answers come only from one person’s work memory.'}</p>
          </div>
          {!persona && (
            <Select value={as} onChange={(e) => setParams(e.target.value ? { as: e.target.value } : {})} aria-label="Whose memory">
              <option value="">Whose memory?</option>
              {(people ?? [])
                .filter((p) => p.status !== 'departed')
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
            </Select>
          )}
        </header>

        {!as ? (
          <p className="text-[15px] leading-6 text-ink-2">Pick a person to ask their memory.</p>
        ) : (
          <>
            <div className="flex flex-1 flex-col gap-7">
              {turns.length === 0 && (
                <div className="rounded-[6px] border border-dashed border-control px-5 py-6 text-[14px] leading-6 text-ink-2">
                  Ask what {persona === as ? 'you' : name} would otherwise have to ask a colleague: why something is set the way it is, how a recurring job is done, who to talk to. If the memory doesn’t hold it, the answer says so and points to who does.
                </div>
              )}
              {turns.map((t, i) => (
                <div key={i} className="flex flex-col gap-3">
                  <div className="max-w-[85%] self-end rounded-[6px] bg-ink px-3.5 py-2 text-[14px] leading-5 text-on-ink">{t.question}</div>
                  {t.error && <p className="text-[13px] text-risk-text">{t.error}</p>}
                  {!t.answer && !t.error && (
                    <div className="flex items-center gap-2 text-[13px] text-ink-3">
                      <span className="size-3 animate-spin rounded-full border-[1.5px] border-line border-t-ink-2" />
                      Reading {name}’s memory…
                    </div>
                  )}
                  {t.answer && (
                    <div className="border-l-2 border-line pl-4">
                      <div className="mb-1.5 flex items-center gap-2">
                        {t.answer.status === 'answered' ? <Chip tone="ok">From memory</Chip> : <Chip tone="idle">Not in memory</Chip>}
                        {t.answer.citations.length > 0 && <span className="font-mono text-[10.5px] text-ink-3">{t.answer.citations.length} source{t.answer.citations.length === 1 ? '' : 's'}</span>}
                      </div>
                      <AnswerText text={t.answer.answer} muted={t.answer.status === 'abstained'} />
                      {t.answer.ask.length > 0 && <p className="mt-2 text-[13.5px] text-ink-2">Ask {t.answer.ask.map((a) => a.name).join(' or ')}: they hold this.</p>}
                      {t.answer.citations.length > 0 && <Sources citations={t.answer.citations} you={name} />}
                    </div>
                  )}
                </div>
              ))}
              <div ref={endRef} />
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                void ask(question)
              }}
              className="sticky bottom-6 mt-10 flex items-center gap-2 rounded-[6px] bg-page py-1.5 pr-1.5 pl-3.5 shadow-[0_0_0_1px_var(--color-control),0_10px_28px_-12px_rgba(0,0,0,0.3)]"
            >
              <input
                value={question}
                autoFocus
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={persona === as ? 'Ask your memory' : `Ask ${name}’s memory`}
                className="h-8 min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-ink-3"
              />
              <button
                type="submit"
                disabled={busy || question.trim().length < 3}
                aria-label="Ask"
                className="flex size-8 items-center justify-center rounded-[4px] bg-ink text-on-ink transition-opacity disabled:opacity-25"
              >
                <ArrowUp size={15} strokeWidth={2} />
              </button>
            </form>
          </>
        )}
      </div>
      {as && profile && <MemoryPanel p={profile} onAsk={(q) => void ask(q)} />}
    </div>
  )
}
