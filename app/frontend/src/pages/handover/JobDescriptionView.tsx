import { Copy, RotateCw } from '../../components/icons'
import { useState } from 'react'
import { Button, Card, CardHeader, ErrorNote, Loading, Panel, Section } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { CADENCE, pct } from '../../lib/format'
import type { JobDescription } from '../../types/api'

function asText(jd: JobDescription): string {
  const lines = [
    jd.title,
    `${jd.team}${jd.reports_to ? ` · Reports to ${jd.reports_to}` : ''}`,
    '',
    jd.summary,
    '',
    "What you'll do",
    ...jd.responsibilities.map((r) => `- ${r.text}`),
    '',
    'You should have',
    ...jd.must.map((s) => `- ${s.name}`),
  ]
  if (jd.nice.length) lines.push('', 'Nice to have', ...jd.nice.map((s) => `- ${s.name}`))
  if (jd.stakeholders.length) lines.push('', "You'll work with", ...jd.stakeholders.map((s) => `- ${s.name}, ${s.org}`))
  return lines.join('\n')
}

/** The JD shaped to WorkIndia's posting form: copy each field into the form. */
function WorkIndiaPost({ jd }: { jd: JobDescription }) {
  const [copied, setCopied] = useState('')
  const fields: [string, string][] = [
    ['Job title', jd.title],
    ['Openings', '1'],
    ['Must-have skills', jd.must.map((s) => s.name).join(', ')],
    ['Description', [jd.summary, ...jd.responsibilities.slice(0, 4).map((r) => `- ${r.text}`)].join('\n')],
  ]
  async function copy(label: string, value: string) {
    await navigator.clipboard.writeText(value)
    setCopied(label)
    setTimeout(() => setCopied(''), 1500)
  }
  return (
    <Card>
      <CardHeader
        title="Post on WorkIndia"
        right={
          <a href="https://www.workindia.in/recruiter/hiring" target="_blank" rel="noreferrer" className="font-medium text-accent hover:underline">
            Open WorkIndia
          </a>
        }
      />
      <dl className="flex flex-col divide-y divide-line">
        {fields.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[140px_minmax(0,1fr)_auto] items-start gap-4 py-2.5 text-[14px]">
            <dt className="text-ink-3">{label}</dt>
            <dd className="line-clamp-3 whitespace-pre-line">{value}</dd>
            <button onClick={() => copy(label, value)} className="text-[13px] font-medium text-accent hover:underline">
              {copied === label ? 'Copied' : 'Copy'}
            </button>
          </div>
        ))}
        <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-4 py-2.5 text-[14px]">
          <dt className="text-ink-3">Salary, location</dt>
          <dd className="text-ink-3">Fill in on WorkIndia. Title, openings and location can't change after posting.</dd>
        </div>
      </dl>
    </Card>
  )
}

export function JobDescriptionView({ id }: { id: string }) {
  const [refresh, setRefresh] = useState(0)
  const path = `/handovers/${encodeURIComponent(id)}/artifacts/jd${refresh ? `?refresh=true&n=${refresh}` : ''}`
  const { data: jd, error, loading } = useApi<JobDescription>(path)
  const [copied, setCopied] = useState(false)

  if (loading && !jd) return <Loading label="Writing the job description from their work" />
  if (error || !jd) return <ErrorNote message={error ?? 'Failed'} />

  async function copy() {
    if (!jd) return
    await navigator.clipboard.writeText(asText(jd))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="flex flex-col gap-12">
      <WorkIndiaPost jd={jd} />
      <div>
        <div className="mb-3 flex items-center justify-between gap-4">
          <p className="text-[13px] text-ink-3">
            Written from <span className="num">{jd.evidence_total}</span> work records
            {jd.model && jd.model !== 'template' ? `, worded by ${jd.model}` : ''}
          </p>
          <div className="flex gap-1">
            <Button variant="ghost" onClick={() => setRefresh((n) => n + 1)} disabled={loading}>
              <RotateCw size={13} strokeWidth={1.75} /> Rewrite
            </Button>
            <Button variant="secondary" onClick={copy}>
              <Copy size={13} strokeWidth={1.75} /> {copied ? 'Copied' : 'Copy'}
            </Button>
          </div>
        </div>

        <Panel className="px-8 py-9 md:px-12 md:py-11">
          <h2 className="text-[26px] leading-8 font-semibold tracking-[-0.02em]">{jd.title}</h2>
          <p className="mt-1 text-[14px] text-ink-2">
            {jd.team}
            {jd.reports_to ? ` · Reports to ${jd.reports_to}` : ''}
          </p>
          <p className="mt-6 max-w-[38rem] text-[16px] leading-6">{jd.summary}</p>

          <h3 className="mt-10 mb-2 text-[14px] font-semibold">What you’ll do</h3>
          <ul className="border-t border-line">
            {jd.responsibilities.map((r) => (
              <li key={r.id} className="flex items-baseline justify-between gap-6 border-b border-line py-2.5 text-[14px]">
                <span>{r.text}</span>
                <span className="num shrink-0 text-[13px] text-ink-3">
                  {[r.cadence && CADENCE[r.cadence], r.share ? `${pct(r.share)} of reports` : `${r.evidence} records`]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-10 grid gap-10 sm:grid-cols-2">
            <div>
              <h3 className="mb-2 text-[14px] font-semibold">You should have</h3>
              <ul className="flex flex-col gap-1.5 text-[14px]">
                {jd.must.map((s) => (
                  <li key={s.id} className="flex items-baseline justify-between gap-4">
                    <span>{s.name}</span>
                    <span className="num shrink-0 text-[13px] text-ink-3">{s.evidence} records</span>
                  </li>
                ))}
              </ul>
              {jd.nice.length > 0 && (
                <>
                  <h3 className="mt-6 mb-2 text-[14px] font-semibold">Nice to have</h3>
                  <ul className="flex flex-col gap-1.5 text-[14px]">
                    {jd.nice.map((s) => (
                      <li key={s.id}>{s.name}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
            <div>
              {jd.stakeholders.length > 0 && (
                <>
                  <h3 className="mb-2 text-[14px] font-semibold">You’ll work with</h3>
                  <ul className="mb-6 flex flex-col gap-2 text-[14px]">
                    {jd.stakeholders.map((s) => (
                      <li key={s.id}>
                        {s.name}, {s.org}
                        {s.context && <div className="text-[13px] text-ink-3">{s.context}</div>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {jd.accounts.length > 0 && (
                <>
                  <h3 className="mb-2 text-[14px] font-semibold">You’ll administer</h3>
                  <ul className="flex flex-col gap-1.5 text-[14px]">
                    {jd.accounts.map((a) => (
                      <li key={a.id}>{a.name}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>
        </Panel>
      </div>

      {jd.diff.old_title && (
        <Section
          title={
            <>
              The old job description missed <span className="num">{jd.diff.missing.length}</span> things they actually did
            </>
          }
          action={jd.diff.old_title}
        >
          <div className="grid gap-10 border-t border-line pt-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-[13px] text-ink-3">Missing from the old one</div>
              <ul className="flex flex-col gap-1.5 text-[14px]">
                {jd.diff.missing.map((m) => (
                  <li key={m.id}>{m.title}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="mb-2 text-[13px] text-ink-3">Asked for, never seen in the work</div>
              <ul className="flex flex-col gap-1.5 text-[14px] text-ink-2">
                {jd.diff.unused.map((u) => (
                  <li key={u} className="line-through decoration-strong">
                    {u}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Section>
      )}
    </div>
  )
}
