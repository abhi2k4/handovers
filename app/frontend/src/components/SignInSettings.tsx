import { useState } from 'react'
import { Check, Copy, Users } from './icons'
import { ComingSoon } from './ComingSoon'
import { PlatformLogo } from './PlatformLogo'
import { useApi } from '../hooks/useApi'
import { READ_ONLY_HINT, useSetupReadOnly, useViewAs } from '../hooks/useViewAs'
import { api } from '../lib/api'
import { Button, Chip } from './ui'

interface Provider {
  id: string
  name: string
  /** The sign-in button: "Continue with <button>". */
  button: string
  guide: string
  /** The directory connector whose values it signs in with; entered there. */
  connector: string
  /** Active: on in Keycloak. At most one provider is. */
  configured: boolean
  /** Its directory card is connected, so it can be made active. */
  ready: boolean | null
  /** Paste this into the provider's app registration (Keycloak's broker endpoint). */
  redirect_uri: string
}

/** HR and IT: sign-in providers (registered in Keycloak, set up by their directory card) and who can sign in. */
export function SignInSettings() {
  const { auth } = useViewAs()
  const { data, error, reload } = useApi<Provider[]>(auth?.sso ? '/auth/providers' : null)
  const { data: planned } = useApi<{ id: string; name: string }[]>(auth?.sso ? '/auth/providers/planned' : null)
  const [sync, setSync] = useState<string | null>(null)
  const readOnly = useSetupReadOnly()

  if (!auth?.sso) {
    return (
      <p className="rounded-[6px] bg-page p-5 text-[14px] text-ink-2 shadow-card">
        Sign-in (Keycloak) is not set up on this server, so people use the guest View as. Run <code className="font-mono text-[13px]">python setup.py</code> and answer yes to sign-in.
      </p>
    )
  }

  async function provision() {
    setSync('Syncing…')
    try {
      const r = await api.post<{ people: number }>('/auth/provision')
      setSync(`${r.people} people can sign in`)
    } catch (e) {
      setSync(e instanceof Error ? e.message : 'Sync failed')
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <p className="text-[14px] text-ink-3">How people sign in. Only people in the company directory can; nobody is created by signing in.</p>
      {error && <p className="text-[13px] text-risk-text">{error}</p>}
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {(data ?? []).map((p) => (
          <ProviderCard
            key={p.id}
            p={p}
            activeOther={(data ?? []).find((o) => o.id !== p.id && o.configured)?.name}
            onChanged={reload}
          />
        ))}
        <li className="flex flex-col gap-3 rounded-[6px] bg-page p-4 shadow-card">
          <div className="flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-[6px] bg-page shadow-[inset_0_0_0_1px_var(--color-line)]">
              <Users size={22} />
            </span>
            <p className="min-w-0 flex-1 text-[15px] font-semibold">People who can sign in</p>
          </div>
          <p className="text-[13px] text-ink-2">{sync ?? 'Everyone in the directory gets an account; people who left are disabled.'}</p>
          <div className="mt-auto pt-1">
            <Button variant="secondary" onClick={() => void provision()} disabled={readOnly} title={readOnly ? READ_ONLY_HINT : undefined}>
              Sync people
            </Button>
          </div>
        </li>
      </ul>
      {planned && planned.length > 0 && <ComingSoon items={planned.map((p) => ({ ...p, label: 'Sign-in' }))} />}
    </section>
  )
}

function ProviderCard({ p, activeOther, onChanged }: { p: Provider; activeOther?: string; onChanged: () => void }) {
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const readOnly = useSetupReadOnly()

  /** Turn sign-in on or off with the connector's values; nothing to enter here. */
  async function toggle() {
    if (!p.configured && activeOther && !confirm(`Make ${p.name} the way people sign in? ${activeOther} is turned off; its settings are kept.`)) return
    setBusy(true)
    setFailure(null)
    try {
      if (p.configured) await api.del(`/auth/providers/${p.id}`)
      else await api.post(`/auth/providers/${p.id}/enable`)
      onChanged()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Could not change sign-in')
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-[6px] bg-page p-4 shadow-card">
      <div className="flex items-start gap-3">
        <PlatformLogo id={p.id} name={p.name} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold">{p.name}</p>
          <p className="text-[12px] text-ink-3">Continue with {p.button}</p>
        </div>
        {p.configured ? <Chip tone="ok">Active</Chip> : <Chip>Inactive</Chip>}
      </div>
      <p className="text-[13px] text-ink-2">{p.guide}</p>
      {!p.configured && (
        <p className="text-[12px] text-ink-3">
          {p.ready === false
            ? 'Connect its card under Directory first.'
            : activeOther
              ? `Settings kept. People sign in with ${activeOther} now.`
              : 'Nobody can sign in this way until it is made active.'}
        </p>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-1">
        <Button
          variant={p.configured ? 'secondary' : 'primary'}
          onClick={() => void toggle()}
          disabled={busy || readOnly || (!p.configured && p.ready === false)}
          title={readOnly ? READ_ONLY_HINT : undefined}
        >
          {p.configured ? 'Deactivate' : 'Make active'}
        </Button>
        <CopyButton text={p.redirect_uri} label="Copy redirect URI" />
      </div>
      {failure && <p className="text-[13px] text-risk-text">{failure}</p>}
    </li>
  )
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <Button
      variant="ghost"
      title={text}
      onClick={() => {
        void navigator.clipboard.writeText(text)
        setCopied(true)
      }}
    >
      {copied ? <Check size={15} /> : <Copy size={15} />} {copied ? 'Copied' : label}
    </Button>
  )
}
