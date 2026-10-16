import { Paperclip } from '../../components/icons'
import { useRef, useState } from 'react'
import { Button, ErrorNote, Loading, Section, TextArea } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { api } from '../../lib/api'
import type { Criterion, Verdict } from '../../types/api'

interface Kit {
  criteria: Criterion[]
}

interface Check {
  verdicts: Verdict[]
  counts: { meets: number; unclear: number; missing: number }
  must_missing: string[]
  method: string
}

const VERDICT: Record<Verdict['verdict'], { label: string; cls: string }> = {
  meets: { label: 'Meets', cls: 'text-ink' },
  unclear: { label: 'Unclear', cls: 'text-soon' },
  missing: { label: 'Missing', cls: 'text-risk-text' },
}

function CriteriaList({ title, list }: { title: string; list: Criterion[] }) {
  if (!list.length) return null
  return (
    <Section title={title} meta={list.length}>
      <ul className="border-t border-line">
        {list.map((c) => (
          <li key={c.id} className="border-b border-line py-2.5">
            <div className="text-[14px] font-medium">{c.label.replace('Hands-on ', '')}</div>
            <div className="text-[13px] text-ink-3">{c.why}</div>
            {c.signals.length > 0 && (
              <div className="mt-1 text-[13px] text-ink-2">On a resume: {c.signals.slice(0, 4).join(', ')}</div>
            )}
          </li>
        ))}
      </ul>
    </Section>
  )
}

export function Screening({ id }: { id: string }) {
  const { data: kit, error, loading } = useApi<Kit>(`/handovers/${encodeURIComponent(id)}/artifacts/screening`)
  const [text, setText] = useState('')
  const [result, setResult] = useState<Check | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  if (loading && !kit) return <Loading />
  if (error || !kit) return <ErrorNote message={error ?? 'Failed'} />

  async function check(file?: File) {
    setBusy(true)
    setErr(null)
    const form = new FormData()
    if (file) form.append('file', file)
    else form.append('text', text)
    try {
      setResult(await api.form<Check>(`/handovers/${encodeURIComponent(id)}/resume-check`, form))
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-12 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div className="flex flex-col gap-10">
        <CriteriaList title="Must have" list={kit.criteria.filter((c) => c.level === 'must')} />
        <CriteriaList title="Nice to have" list={kit.criteria.filter((c) => c.level === 'nice')} />
      </div>

      <Section title="Check a resume" action="Per criterion, never an overall score">
        <div className="border-t border-line pt-4">
          <TextArea rows={8} placeholder="Paste a resume" value={text} onChange={(e) => setText(e.target.value)} />
          <div className="mt-2.5 flex items-center gap-2">
            <Button onClick={() => check()} disabled={busy || text.trim().length < 20}>
              {busy ? 'Checking…' : 'Check'}
            </Button>
            <Button variant="ghost" onClick={() => fileRef.current?.click()} disabled={busy}>
              <Paperclip size={13} strokeWidth={1.75} /> Attach PDF or Word
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && check(e.target.files[0])}
            />
          </div>
          {err && <p className="mt-3 text-[13px] text-risk-text">{err}</p>}
        </div>

        {result && (
          <div className="mt-8">
            <p className="mb-3 text-[14px] text-ink-2">
              Meets <span className="num text-ink">{result.counts.meets}</span>, unclear on{' '}
              <span className="num text-ink">{result.counts.unclear}</span>, missing{' '}
              <span className="num text-ink">{result.counts.missing}</span>.
              {result.must_missing.length > 0 && ` Missing a must-have: ${result.must_missing.join(', ').replaceAll('Hands-on ', '')}.`}
            </p>
            <ul className="border-t border-line">
              {result.verdicts.map((v) => (
                <li key={v.id} className="grid grid-cols-[64px_minmax(0,1fr)] gap-3 border-b border-line py-2.5">
                  <span className={`text-[13px] leading-5 font-medium ${VERDICT[v.verdict].cls}`}>{VERDICT[v.verdict].label}</span>
                  <div className="min-w-0">
                    <div className="text-[14px] leading-5">{v.label.replace('Hands-on ', '')}</div>
                    {v.quote && <p className="mt-0.5 text-[13px] text-ink-2">“{v.quote}”</p>}
                    {!v.quote && v.ask && <p className="mt-0.5 text-[13px] text-ink-3">{v.ask}</p>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>
    </div>
  )
}
