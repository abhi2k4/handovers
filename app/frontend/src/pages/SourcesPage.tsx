import { Database, Inbox, PlugsConnected, Upload } from '../components/icons'
import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { StatBand } from '../components/StatBand'
import { Button, Card, CardHeader, Chip, Empty, PageHeader, Select } from '../components/ui'
import { Pager } from '../components/Pager'
import { useApi } from '../hooks/useApi'
import { useViewAs } from '../hooks/useViewAs'
import { usePaged } from '../hooks/usePaged'
import { api } from '../lib/api'
import { date } from '../lib/format'
import type { PersonRow } from '../types/api'

interface UploadRow {
  id: string
  title: string
  kind: string
  at: number
  employee: string | null
  facts: number
}

interface ReviewRow {
  id: string
  kind: string
  title: string
  confidence: number
  employee: string
  quote: string | null
  source: string
}

interface UploadResult {
  file: string
  written: number
  review: number
  method: string
}

interface Meta {
  graph: Record<string, number>
  reset_enabled: boolean
}

interface ConnectorRow {
  id: string
  name: string
  configured: boolean
  state: { status: 'ok' | 'error' } | null
}

function ReviewItem({
  r,
  people,
  decide,
}: {
  r: ReviewRow
  people: PersonRow[]
  decide: (id: string, approve: boolean, who?: string) => Promise<void>
}) {
  const [who, setWho] = useState(r.employee)
  return (
    <li className="grid gap-3 border-b border-line py-3 last:border-0 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
      <div className="min-w-0">
        <div className="text-[14px] font-medium">
          {r.title} <span className="font-normal text-ink-3">· {r.kind}</span>
        </div>
        {r.quote && <p className="mt-0.5 text-[13px] text-ink-2">“{r.quote}”</p>}
        <p className="mt-0.5 text-[13px] text-ink-3">{r.source}</p>
      </div>
      <div className="flex items-center gap-2">
        <Select value={who} onChange={(e) => setWho(e.target.value)} aria-label="Whose work">
          <option value="">Whose work?</option>
          {people.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
        <Button variant="ghost" onClick={() => decide(r.id, false)}>
          Discard
        </Button>
        <Button variant="secondary" onClick={() => decide(r.id, true, who)} disabled={!who}>
          Add to memory
        </Button>
      </div>
    </li>
  )
}

export function SourcesPage() {
  const { data: people } = useApi<PersonRow[]>('/people')
  const uploads = useApi<UploadRow[]>('/uploads')
  const review = useApi<ReviewRow[]>('/review')
  const meta = useApi<Meta>('/meta')
  const { has } = useViewAs()
  const connectors = useApi<ConnectorRow[]>(has('platform_admin') ? '/connectors' : null)
  const live = (connectors.data ?? []).filter((c) => c.configured)
  // Only the platform admin manages integrations; for everyone else the list is forbidden, so no link to it.
  const manages = has('platform_admin') && !connectors.error
  const reviewPage = usePaged(review.data ?? [], 8)
  const uploadPage = usePaged(uploads.data ?? [], 10)
  const [employee, setEmployee] = useState('')
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const [last, setLast] = useState<UploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function upload(file: File) {
    setBusy(true)
    setError(null)
    const form = new FormData()
    form.append('file', file)
    form.append('employee_id', employee)
    try {
      setLast(await api.form<UploadResult>('/uploads', form))
      uploads.reload()
      review.reload()
      meta.reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function decide(id: string, approve: boolean, who?: string) {
    await api.post(`/review/${encodeURIComponent(id)}`, { approve, employee_id: who || null })
    review.reload()
  }

  return (
    <>
      <PageHeader title="Sources" />
      <div className="mb-4">
        <StatBand
          figures={[
            { label: 'Work records', value: meta.data?.graph.Source ?? '–', icon: Database },
            { label: 'Uploaded', value: uploads.data?.length ?? 0, icon: Upload },
            { label: 'To review', value: review.data?.length ?? 0, tone: (review.data?.length ?? 0) > 0 ? 'text-soon' : undefined, icon: Inbox },
            {
              label: 'Connected tools',
              value: manages ? live.length : '–',
              note: manages ? `of ${connectors.data?.length ?? 0}` : 'Set up by your platform admin',
              href: manages ? '/integrations' : undefined,
              icon: PlugsConnected,
              meter: connectors.data?.length ? { value: live.length, max: connectors.data.length } : undefined,
            },
          ]}
        />
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <Card>
            <label
              onDragOver={(e) => {
                e.preventDefault()
                setDrag(true)
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDrag(false)
                const f = e.dataTransfer.files?.[0]
                if (f) void upload(f)
              }}
              className={`flex cursor-pointer flex-col items-center gap-2 rounded-[4px] px-6 py-10 text-center transition-colors duration-150 ${
                drag ? 'bg-accent-soft' : 'bg-app hover:bg-hover'
              } shadow-[inset_0_0_0_1px_var(--color-line)]`}
            >
              <Upload size={18} strokeWidth={1.5} className="text-ink-3" />
              <span className="text-[14px] font-medium">{busy ? 'Reading…' : 'Drop a file, or choose one'}</span>
              <span className="text-[13px] text-ink-3">PDF, Word, PowerPoint, Excel, CSV or text</span>
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.pptx,.xlsx,.xls,.csv,.txt,.md"
                onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
              />
            </label>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <Select value={employee} onChange={(e) => setEmployee(e.target.value)} aria-label="Whose work">
                <option value="">Whose work is it? (optional)</option>
                {(people ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
              {last && (
                <p className="text-[13px] text-ink-2">
                  {last.file}: <span className="num text-ink">{last.written}</span> facts added
                  {last.review ? (
                    <>
                      , <span className="num text-ink">{last.review}</span> to review
                    </>
                  ) : null}
                </p>
              )}
              {error && <p className="text-[13px] text-risk-text">{error}</p>}
            </div>
          </Card>

          {(review.data?.length ?? 0) > 0 && (
            <Card>
              <CardHeader title="To review" meta={review.data?.length} />
              <ul>
                {reviewPage.items.map((r) => (
                  <ReviewItem key={r.id} r={r} people={people ?? []} decide={decide} />
                ))}
              </ul>
              <Pager p={reviewPage} noun="facts" />
            </Card>
          )}

          <Card>
            <CardHeader title="Uploaded" />
            {uploads.data?.length ? (
              <>
              <ul>
                {uploadPage.items.map((u) => (
                  <li key={u.id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-6 border-b border-line py-2.5 text-[14px] last:border-0">
                    <span className="truncate">{u.title}</span>
                    <span className="num text-[13px] text-ink-2">{u.facts} facts</span>
                    <span className="num text-[13px] text-ink-3">{date(u.at, true)}</span>
                  </li>
                ))}
              </ul>
              <Pager p={uploadPage} noun="uploads" />
              </>
            ) : (
              <Empty>Nothing uploaded yet.</Empty>
            )}
          </Card>
        </div>

        <aside className="flex flex-col gap-4">
          <Card>
            <CardHeader title="Integrations" right={manages ? <Link to="/integrations" className="text-accent">Manage</Link> : undefined} />
            {!manages && <Empty>Your platform admin connects Slack, Google Drive, GitHub and other tools. What they bring in shows up here as work records.</Empty>}
            <ul>
              {(connectors.data ?? []).map((c) => (
                <li key={c.id} className="flex items-center justify-between border-b border-line py-2 text-[14px] last:border-0">
                  <span>{c.name}</span>
                  {!c.configured ? (
                    <Chip>Not connected</Chip>
                  ) : c.state?.status === 'error' ? (
                    <Chip tone="risk">Sync failed</Chip>
                  ) : (
                    <Chip tone="ok">Connected</Chip>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        </aside>
      </div>
    </>
  )
}
