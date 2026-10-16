import { useState } from 'react'
import type { ReactNode } from 'react'
import { Check, Copy, Envelope } from './icons'
import { PlatformLogo } from './PlatformLogo'
import { useApi } from '../hooks/useApi'
import { READ_ONLY_HINT, useSetupReadOnly } from '../hooks/useViewAs'
import { api } from '../lib/api'
import { Button, Chip, Input } from './ui'

/* Integrations → Alerts (platform admin): how alerts leave the app. One card per channel (WhatsApp,
   email) with its settings, Test and a master switch (backend services/delivery.py). People still
   choose their own number, email and alert types on their Alerts page. */

interface Field {
  key: string
  label: string
  secret: boolean
  placeholder: string
  hint: string
  set: boolean
  value: string
  source: 'app' | 'server' | null
}

interface Channel {
  channel: string
  /** The master switch: off, nobody gets this channel and alerts stay in the app. */
  enabled: boolean
  configured: boolean
  fields: Field[]
  /** WhatsApp only: what to register in Meta. */
  webhook_url: string | null
}

export function AlertDelivery() {
  return (
    <section className="flex flex-col gap-4">
      <p className="text-[14px] text-ink-3">How alerts leave the app. Every alert also shows in the app. People choose their own number, email and alert types on their Alerts page.</p>
      <div className="grid gap-3 xl:grid-cols-2">
        <ChannelCard
          channel="whatsapp"
          name="WhatsApp"
          via="Meta WhatsApp Cloud API"
          logo={<PlatformLogo id="whatsapp" name="WhatsApp" />}
          on="Alerts go to each person’s WhatsApp with buttons to act on them, outside their quiet hours."
        />
        <ChannelCard
          channel="email"
          name="Email"
          via="SMTP · Mailpit in development"
          logo={
            <span className="flex size-10 shrink-0 items-center justify-center rounded-[6px] bg-page shadow-[inset_0_0_0_1px_var(--color-line)]">
              <Envelope size={22} className="text-accent" />
            </span>
          }
          on="Alerts are emailed to each person’s work address, with a link back to the app."
        />
      </div>
    </section>
  )
}

function ChannelCard({ channel, name, via, logo, on }: { channel: string; name: string; via: string; logo: ReactNode; on: string }) {
  const { data, error, reload } = useApi<Channel>(`/alerts/delivery/${channel}`)
  const readOnly = useSetupReadOnly()
  const lock = readOnly ? READ_ONLY_HINT : undefined
  const [values, setValues] = useState<Record<string, string> | null>(null)
  const [busy, setBusy] = useState<'save' | 'switch' | 'test' | null>(null)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [copied, setCopied] = useState(false)

  if (error) return <p className="text-[13px] text-risk-text">{error}</p>
  if (!data) return null
  // Plain fields start with their current value; secrets start empty (blank keeps the stored one).
  const form = values ?? Object.fromEntries(data.fields.map((f) => [f.key, f.secret ? '' : f.value]))
  const path = `/alerts/delivery/${channel}`

  async function run(kind: 'save' | 'switch' | 'test') {
    if (kind === 'switch' && data?.enabled && !confirm(`Turn ${name} alerts off for everyone? Alerts stay in the app.`)) return
    setBusy(kind)
    setResult(null)
    try {
      if (kind === 'test') setResult(await api.post<{ ok: boolean; message: string }>(`${path}/test`))
      else await api.put(path, kind === 'save' ? { values: form } : { enabled: !data?.enabled })
      if (kind !== 'test') {
        setValues(null)
        reload()
      }
    } catch (e) {
      setResult({ ok: false, message: e instanceof Error ? e.message : 'That did not work' })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-[6px] bg-page p-4 shadow-card">
      <div className="flex items-start gap-3">
        {logo}
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-semibold">{name}</p>
          <p className="text-[12px] text-ink-3">{via}</p>
        </div>
        {!data.enabled ? <Chip tone="risk">Off for everyone</Chip> : data.configured ? <Chip tone="ok">On</Chip> : <Chip>Not set up</Chip>}
      </div>
      <p className="text-[13px] text-ink-2">{data.enabled ? on : `Turned off: nobody gets ${name} alerts. Every alert still shows in the app.`}</p>
      {data.webhook_url && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium">Webhook URL (register in Meta, with the verify token)</span>
          <span className="flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-[4px] bg-app px-3 py-2 font-mono text-[12px] shadow-[inset_0_0_0_1px_var(--color-line)]">{data.webhook_url}</code>
            <Button
              variant="ghost"
              onClick={() => {
                void navigator.clipboard.writeText(data.webhook_url ?? '')
                setCopied(true)
              }}
            >
              {copied ? <Check size={15} /> : <Copy size={15} />} {copied ? 'Copied' : 'Copy'}
            </Button>
          </span>
        </div>
      )}
      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault()
          void run('save')
        }}
      >
        {data.fields.map((f) => (
          <label key={f.key} className="flex flex-col gap-1">
            <span className="text-[13px] font-medium">{f.label}</span>
            <Input
              type={f.secret ? 'password' : 'text'}
              autoComplete="off"
              spellCheck={false}
              disabled={readOnly}
              value={form[f.key] ?? ''}
              placeholder={f.secret && f.set ? `${f.value} (leave blank to keep)` : f.placeholder}
              onChange={(e) => setValues({ ...form, [f.key]: e.target.value })}
            />
            {(f.hint || f.source === 'server') && (
              <span className="text-[12px] text-ink-3">
                {f.hint}
                {f.source === 'server' ? ' Set on the server; a value here replaces it.' : ''}
              </span>
            )}
          </label>
        ))}
        <button type="submit" hidden />
      </form>
      <div className="mt-auto flex flex-wrap gap-2 pt-1">
        <Button onClick={() => void run('save')} disabled={busy !== null || readOnly || values === null} title={lock}>
          {busy === 'save' ? 'Saving' : 'Save'}
        </Button>
        <Button variant="ghost" onClick={() => void run('test')} disabled={busy !== null || readOnly || !data.configured} title={lock}>
          {busy === 'test' ? 'Testing' : 'Test'}
        </Button>
        <Button variant="ghost" onClick={() => void run('switch')} disabled={busy !== null || readOnly} title={lock}>
          {data.enabled ? 'Turn off for everyone' : 'Turn on'}
        </Button>
      </div>
      {result && <p className={`text-[13px] ${result.ok ? 'text-ok-text' : 'text-risk-text'}`}>{result.message}</p>}
    </div>
  )
}
