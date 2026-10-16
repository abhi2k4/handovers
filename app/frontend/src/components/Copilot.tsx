import { ArrowUp, BookOpen, Brain, LoaderCircle, Sparkles, X } from './icons'
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useApi } from '../hooks/useApi'
import { useViewAs } from '../hooks/useViewAs'
import { api } from '../lib/api'

interface CopilotCitation {
  id: string
  title: string
  via: string
  from: string | null
  approved_by: string | null
}

interface CopilotAnswer {
  source: 'memory' | 'guide'
  status: 'answered' | 'abstained'
  answer: string
  method: string
  citations: CopilotCitation[]
  ask: { id: string; name: string; title?: string }[]
  note?: string | null
}

/** Which page the copilot is on, for page-aware answers and suggestions. */
function pageKey(path: string): string {
  if (path === '/') return 'home'
  const [, first, second] = path.split('/')
  if (first === 'people') return second ? 'person' : 'people'
  if (first === 'handovers') return second ? 'handover' : 'handovers'
  return first || 'home'
}

// Work questions that the sample company's memory can answer, per demo person.
const WORK_EXAMPLES: Record<string, string[]> = {
  'emp:ananya': ['What is our CAC target and why?', 'Why did we pause Google Ads?'],
  'emp:nisha': ['What is our CAC target and why?', 'How do I do the month-end UTM rebuild?'],
  'emp:arjun': ['Why does the reconciliation service retry only 3 times?', 'How do I unstick a ledger export batch?'],
  'emp:farhan': ['Why does the reconciliation service retry only 3 times?', 'Who is our contact at AcmeBank?'],
}

/** "Ask anything" on every page, grounded in the app guide and the asker's own memory. */
export function CopilotBar() {
  const location = useLocation()
  const page = pageKey(location.pathname)
  const { persona } = useViewAs()
  const { data: pageSuggestions } = useApi<string[]>(`/copilot/suggestions?page=${page}`)
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ q: string; a?: CopilotAnswer; error?: string } | null>(null)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  async function ask(q: string) {
    if (!q.trim() || busy) return
    setOpen(true)
    setBusy(true)
    setQuestion('')
    setResult({ q })
    try {
      const a = await api.post<CopilotAnswer>('/copilot', { question: q, page })
      setResult({ q, a })
    } catch (e) {
      setResult({ q, error: e instanceof Error ? e.message : 'Something went wrong' })
    } finally {
      setBusy(false)
    }
  }

  const suggestions = [...(pageSuggestions ?? []), ...(WORK_EXAMPLES[persona] ?? [])]

  return (
    <div ref={box} className="relative w-full max-w-[720px] flex-1">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void ask(question)
        }}
        className="flex h-10 items-center gap-2 rounded-[6px] bg-page pr-1.5 pl-3 shadow-[inset_0_0_0_1px_var(--color-control),0_1px_2px_rgba(15,27,45,0.04)] focus-within:shadow-[inset_0_0_0_1px_var(--color-accent-fill),0_0_0_3px_var(--color-accent-soft)]"
      >
        <Sparkles size={16} strokeWidth={1.75} className="shrink-0 text-accent" />
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Ask anything about this page or your work…"
          aria-label="Ask the copilot"
          className="min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-ink-3"
        />
        <button
          type="submit"
          disabled={!question.trim() || busy}
          aria-label="Ask"
          className="flex size-7 items-center justify-center rounded-[4px] bg-accent-fill text-white transition-opacity disabled:opacity-30"
        >
          {busy ? <LoaderCircle size={14} className="animate-spin" /> : <ArrowUp size={14} />}
        </button>
      </form>

      {open && (
        <div className="absolute inset-x-0 top-12 z-40 rounded-[6px] bg-page p-4 shadow-[0_0_0_1px_var(--color-line),0_16px_40px_-12px_rgba(15,27,45,0.22)]">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[12px] font-medium text-ink-3">Copilot</span>
            <button onClick={() => setOpen(false)} aria-label="Close" className="rounded-[4px] p-1 text-ink-3 hover:bg-hover hover:text-ink">
              <X size={14} />
            </button>
          </div>

          {result && (
            <div className="mb-4 rounded-[6px] bg-app p-3.5">
              <div className="mb-1.5 text-[13px] font-medium text-ink-2">{result.q}</div>
              {busy && !result.a && <div className="text-ink-3">Thinking…</div>}
              {result.error && <div className="text-risk-text">{result.error}</div>}
              {result.a && <AnswerView a={result.a} />}
            </div>
          )}

          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => void ask(s)}
                className="rounded-[3px] bg-page px-2.5 py-1 text-[12.5px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)] transition-colors hover:bg-hover hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
          <div className="mt-3 text-[12px] text-ink-3">
            Answers come only from the app guide{persona ? ' and your own memory, with sources' : ''}.
          </div>
        </div>
      )}
    </div>
  )
}

function AnswerView({ a }: { a: CopilotAnswer }) {
  const Icon = a.source === 'memory' ? Brain : BookOpen
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[14px] leading-5 whitespace-pre-line text-ink">{a.answer}</p>
      {a.citations.length > 0 && (
        <ul className="flex flex-col gap-1">
          {a.citations.slice(0, 3).map((c) => (
            <li key={c.id} className="text-[13px] text-ink-2">
              <span className="font-medium text-ink">{c.title}</span>
              {c.via === 'transfer' && c.from && (
                <span className="text-ink-3">
                  {' '}
                  · from {c.from}
                  {c.approved_by ? `, approved by ${c.approved_by}` : ''}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {a.status === 'abstained' && a.ask.length > 0 && (
        <div className="text-[13px] text-ink-2">Ask: {a.ask.map((p) => p.name).join(', ')}</div>
      )}
      {a.note && <div className="text-[13px] text-soon">{a.note}</div>}
      <div className="flex items-center justify-between text-[12px] text-ink-3">
        <span className="flex items-center gap-1">
          <Icon size={12} />
          {a.source === 'memory' ? 'From your memory' : 'From the app guide'} · {a.method}
        </span>
        {a.source === 'memory' && (
          <Link to="/ask" className="text-accent">
            Open in Ask
          </Link>
        )}
      </div>
    </div>
  )
}
