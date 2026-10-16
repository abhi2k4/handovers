import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Check, Checks, Envelope, WhatsappLogo } from '../components/icons'
import { Button, Card, CardHeader, ErrorNote, Input, PageSkeleton, Segmented, Select } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { useViewAs } from '../hooks/useViewAs'
import { api } from '../lib/api'

type Mode = 'instant' | 'digest' | 'off'

interface Settings {
  phone: string
  modes: Record<string, Mode>
  quiet_from: number
  quiet_to: number
  kinds: { key: string; label: string }[]
  whatsapp: boolean
  /** Also email this person's alerts (when the platform admin has email on). */
  email: boolean
  email_channel: boolean
  email_address: string
}

interface Alert {
  id: string
  kind: string
  at: number
  status: 'sent' | 'app' | 'held' | 'digest' | 'failed'
  title: string
  body: string
  buttons: { id: string; label: string }[]
  acted: string | null
  error: string | null
}

const MODES: { value: Mode; label: string }[] = [
  { value: 'instant', label: 'Instant' },
  { value: 'digest', label: 'Digest' },
  { value: 'off', label: 'Off' },
]

const STATUS: Record<Alert['status'], string> = {
  sent: 'WhatsApp',
  app: 'In app',
  held: 'Held for quiet hours',
  digest: 'In the daily digest',
  failed: 'WhatsApp failed',
}

const time = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const HOURS = Array.from({ length: 24 }, (_, h) => h)

function Message({ a, onAct }: { a: Alert; onAct: (a: Alert, button: string) => void }) {
  return (
    <li className="max-w-[420px]">
      <div className="rounded-[6px] rounded-tl-[4px] bg-[#e7f6ee] px-3.5 py-2.5 dark:bg-[#12291f]">
        <div className="text-[14px] font-semibold">{a.title}</div>
        <div className="mt-0.5 text-[14px] whitespace-pre-line text-ink-2">{a.body}</div>
        <div className="mt-1 flex items-center justify-end gap-1 text-[11px] text-ink-3">
          {time.format(new Date(a.at))} · {a.status === 'failed' && a.error ? a.error : STATUS[a.status]}
          {a.status === 'sent' && <Checks size={14} className="text-accent" />}
        </div>
      </div>
      {a.buttons.length > 0 && (
        <div className="mt-1 grid gap-1" style={{ gridTemplateColumns: `repeat(${a.buttons.length}, minmax(0, 1fr))` }}>
          {a.buttons.map((b) => (
            <button
              key={b.id}
              onClick={() => onAct(a, b.id)}
              disabled={!!a.acted && !b.id.startsWith('open:')}
              className="flex h-9 items-center justify-center gap-1 rounded-[6px] bg-page text-[13px] font-medium text-accent shadow-card hover:bg-hover disabled:text-ink-3"
            >
              {a.acted === b.id && <Check size={13} strokeWidth={2.5} />}
              {b.label}
            </button>
          ))}
        </div>
      )}
    </li>
  )
}

function SettingsCard({ s, onSaved }: { s: Settings; onSaved: () => void }) {
  const [phone, setPhone] = useState(s.phone)
  const [email, setEmail] = useState(s.email)
  const [modes, setModes] = useState(s.modes)
  const [quiet, setQuiet] = useState({ from: s.quiet_from, to: s.quiet_to })
  const [note, setNote] = useState('')

  async function save() {
    try {
      await api.put('/alerts/settings', { phone, email, modes, quiet_from: quiet.from, quiet_to: quiet.to })
      setNote('Saved')
      onSaved()
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <Card>
      <CardHeader
        title="Settings"
        right={
          <span className={`flex items-center gap-1.5 ${s.whatsapp ? 'text-ok-text' : ''}`}>
            <WhatsappLogo size={16} /> {s.whatsapp ? 'Connected' : 'Not connected'}
          </span>
        }
      />
      <label className="mb-5 block">
        <span className="mb-1.5 block text-[13px] font-medium">WhatsApp number</span>
        <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98765 43210" inputMode="tel" />
      </label>
      {s.email_channel && s.email_address && (
        <label className="mb-5 flex items-center gap-2.5 text-[14px]">
          <input type="checkbox" checked={email} onChange={(e) => setEmail(e.target.checked)} className="size-4 accent-[var(--color-accent-fill)]" />
          <Envelope size={16} className="text-ink-3" />
          Also email me at <span className="font-medium">{s.email_address}</span>
        </label>
      )}
      <ul className="flex flex-col divide-y divide-line">
        {s.kinds.map((k) => (
          <li key={k.key} className="flex items-center justify-between gap-4 py-2.5">
            <span className="text-[14px]">{k.label}</span>
            <Segmented
              value={modes[k.key]}
              options={k.key === 'digest' ? MODES.filter((m) => m.value !== 'digest') : MODES}
              onChange={(m) => setModes({ ...modes, [k.key]: m })}
            />
          </li>
        ))}
      </ul>
      <div className="mt-4 flex items-center gap-2 text-[14px]">
        <span className="flex-1">Quiet hours</span>
        <Select value={quiet.from} onChange={(e) => setQuiet({ ...quiet, from: Number(e.target.value) })} aria-label="Quiet from">
          {HOURS.map((h) => (
            <option key={h} value={h}>{`${h}:00`}</option>
          ))}
        </Select>
        <span className="text-ink-3">to</span>
        <Select value={quiet.to} onChange={(e) => setQuiet({ ...quiet, to: Number(e.target.value) })} aria-label="Quiet to">
          {HOURS.map((h) => (
            <option key={h} value={h}>{`${h}:00`}</option>
          ))}
        </Select>
      </div>
      <div className="mt-5 flex items-center justify-end gap-3">
        {note && <span className="text-[13px] text-ink-3">{note}</span>}
        <Button onClick={save}>Save</Button>
      </div>
    </Card>
  )
}

export function AlertsPage() {
  const { persona, has } = useViewAs()
  const navigate = useNavigate()
  const settings = useApi<Settings>(persona ? '/alerts/settings' : null)
  const inbox = useApi<Alert[]>(persona ? '/alerts' : null)
  const [error, setError] = useState('')

  if (!persona) return <ErrorNote message="Choose who you are in View as to see your alerts." />
  if (!settings.data || !inbox.data) return <PageSkeleton />

  async function act(a: Alert, button: string) {
    setError('')
    try {
      const r = await api.post<{ href?: string }>(`/alerts/${a.id}/act`, { button })
      if (r.href) navigate(r.href)
      else inbox.reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }

  async function send(path: string) {
    setError('')
    try {
      await api.post(path)
      inbox.reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="mb-2 flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-[26px] leading-8 font-semibold tracking-[-0.02em]">Alerts</h1>
        <div className="flex gap-2">
          {has('hr') && (
            <Button variant="secondary" onClick={() => send('/alerts/digest')}>
              Send today's digest
            </Button>
          )}
          <Button variant="secondary" onClick={() => send('/alerts/test')}>
            Send a test
          </Button>
        </div>
      </header>
      {error && <ErrorNote message={error} />}
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Messages" meta={inbox.data.length || undefined} />
          {inbox.data.length === 0 ? (
            <p className="text-[14px] text-ink-2">Nothing yet.</p>
          ) : (
            <ul className="flex flex-col gap-4">
              {inbox.data.map((a) => (
                <Message key={a.id} a={a} onAct={act} />
              ))}
            </ul>
          )}
        </Card>
        <SettingsCard s={settings.data} onSaved={settings.reload} />
      </div>
    </div>
  )
}
