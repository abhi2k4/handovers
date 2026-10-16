import { useRef, useState } from 'react'
import { Check, Upload } from '../../components/icons'
import { Button, Card, CardHeader, Chip, ErrorNote, Loading, Segmented } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { api } from '../../lib/api'

interface Verdict {
  id: string
  label: string
  level: 'must' | 'nice'
  verdict: 'meets' | 'missing' | 'unclear'
}

interface Candidate {
  id: string
  name: string
  phone: string
  city: string
  summary: string
  source: string
  must_met: number
  must_total: number
  verdicts: Verdict[]
}

function Row({ c }: { c: Candidate }) {
  const [open, setOpen] = useState(false)
  const all = c.must_total > 0 && c.must_met === c.must_total
  return (
    <li className="py-3">
      <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-4">
        <button onClick={() => setOpen((o) => !o)} className="min-w-0 text-left">
          <span className="block truncate text-[14px] font-medium">{c.name}</span>
          <span className="block truncate text-[13px] text-ink-3">
            {[c.city, c.source].filter(Boolean).join(' · ')}
          </span>
        </button>
        <Chip tone={all ? 'ok' : c.must_met > 0 ? 'soon' : 'idle'}>
          {c.must_met}/{c.must_total} must-haves
        </Chip>
        {c.phone ? (
          <a href={`tel:+91${c.phone.slice(-10)}`} className="text-[13px] font-medium text-accent hover:underline">
            Call
          </a>
        ) : (
          <span />
        )}
      </div>
      {open && (
        <div className="mt-2 rounded-[4px] bg-app p-3 text-[13px]">
          <p className="mb-2 text-ink-2">{c.summary}</p>
          <ul className="grid gap-1 sm:grid-cols-2">
            {c.verdicts
              .filter((v) => v.level === 'must')
              .map((v) => (
                <li key={v.id} className={`flex items-center gap-1.5 ${v.verdict === 'meets' ? 'text-ok-text' : 'text-ink-3'}`}>
                  {v.verdict === 'meets' ? <Check size={12} strokeWidth={2.5} /> : <span className="w-3 text-center">–</span>}
                  {v.label}
                </li>
              ))}
          </ul>
        </div>
      )}
    </li>
  )
}

/** Candidates for the vacancy, from the job board's CSV export, checked against the real must-haves. */
export function CandidatesView({ id }: { id: string }) {
  const path = `/handovers/${encodeURIComponent(id)}/candidates`
  const { data, error, reload } = useApi<Candidate[]>(path)
  const [filter, setFilter] = useState<'all' | 'strong'>('all')
  const [note, setNote] = useState('')
  const file = useRef<HTMLInputElement>(null)
  if (error) return <ErrorNote message={error} />
  if (!data) return <Loading />

  async function done(p: Promise<{ imported: number; new: number; strong: number }>) {
    setNote('')
    try {
      const r = await p
      setNote(`${r.new} new · ${r.strong} with every must-have${r.strong ? ', HR alerted' : ''}`)
      reload()
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Failed')
    }
  }

  async function upload(f: File) {
    await done(api.post(path, { csv: await f.text(), source: 'WorkIndia' }))
  }

  const strong = data.filter((c) => c.must_total > 0 && c.must_met === c.must_total)
  const shown = filter === 'strong' ? strong : data
  return (
    <Card>
      <CardHeader
        title="Candidates"
        meta={data.length || undefined}
        right={
          <>
            <input ref={file} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <Button variant="ghost" onClick={() => done(api.post(`${path}/sample`))}>
              Sample export
            </Button>
            <Button variant="secondary" onClick={() => file.current?.click()}>
              <Upload size={14} /> Import WorkIndia CSV
            </Button>
          </>
        }
      />
      {note && <p className="mb-3 text-[13px] text-ink-2">{note}</p>}
      {data.length === 0 ? (
        <p className="text-[14px] text-ink-2">Export candidate profiles from your WorkIndia dashboard, then import the file here.</p>
      ) : (
        <>
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: 'all', label: 'All', count: data.length },
              { value: 'strong', label: 'Every must-have', count: strong.length },
            ]}
          />
          <ul className="mt-2 flex flex-col divide-y divide-line">
            {shown.map((c) => (
              <Row key={c.id} c={c} />
            ))}
          </ul>
        </>
      )}
    </Card>
  )
}
