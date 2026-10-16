import { APP_BASE } from '../app/base'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { ArrowsClockwise, Lock } from '../components/icons'
import { AlertDelivery } from '../components/AlertDelivery'
import { ComingSoon } from '../components/ComingSoon'
import { PlatformLogo, PlatformMark } from '../components/PlatformLogo'
import { SignInSettings } from '../components/SignInSettings'
import { Button, Chip, ErrorNote, Input, Modal, PageHeader, PageSkeleton, Segmented } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { READ_ONLY_HINT, useSetupReadOnly } from '../hooks/useViewAs'
import { api } from '../lib/api'
import { date } from '../lib/format'

interface ConnectorState {
  status: 'ok' | 'error' | null
  last_sync: number | null
  sources: number | null
  facts: number | null
  review: number | null
  people: number | null
  error: string | null
  /** The active one in its category (a directory); only it syncs. */
  active: boolean
  /** The last Test of the saved settings; cleared when they change. */
  test_ok: boolean | null
  test_message: string | null
  tested_at: number | null
}

interface Field {
  key: string
  label: string
  secret: boolean
  placeholder: string
  hint: string
  set: boolean
  /** Plain value, or `••••1234` for a secret. Secrets are never sent in full. */
  value: string
  source: 'app' | 'server' | null
}

interface Planned {
  id: string
  name: string
  category: string
}

/** Directory and HR systems create the people; everything else is evidence about their work. */
const PEOPLE = new Set(['directory', 'hr'])

interface Team {
  id: string
  name: string
}

/** One connected account of a platform; the first one's id is the platform id. */
interface Account {
  id: string
  /** What the admin calls it ("Sales Jira"); null for a platform connected once. */
  label: string | null
  /** Teams its records are attributed to. */
  teams: Team[]
  configured: boolean
  fields: Field[]
  state: ConnectorState | null
}

interface Connector {
  id: string
  name: string
  category: string
  configured: boolean
  /** One active at a time in its category (directories). */
  exclusive: boolean
  fields: Field[]
  /** Every account, first one first. Work tools can have several; directories one. */
  accounts: Account[]
  state: ConnectorState | null
}

/** What each platform teaches the graph, in one line. */
const BRINGS: Record<string, string> = {
  entra: 'People, titles, teams and managers. Also signs them in with Microsoft',
  google_workspace: 'People, titles, teams and managers. Also signs them in with Google',
  slack: 'Decisions and know-how from channel threads',
  github: 'Who changes and reviews which code',
  jira: 'Who fixes what, and fixes that keep coming back',
  notion: 'Runbooks, decision records and specs',
  hubspot: 'Which customer relationships each person owns',
  salesforce: 'Which accounts and deals each person owns',
}

const CATEGORY: Record<string, string> = {
  directory: 'Directory',
  chat: 'Chat',
  code: 'Code',
  tickets: 'Tickets',
  docs: 'Docs',
  crm: 'CRM',
  hr: 'HR',
}

type Tab = 'directory' | 'tools' | 'signin' | 'alerts' | 'sample'
const TABS: Tab[] = ['directory', 'tools', 'signin', 'alerts', 'sample']

/** Platform admin: set up the organisation, one area per tab, so nothing needs a long scroll. */
export function IntegrationsPage() {
  const { data, error, loading, reload } = useApi<Connector[]>('/connectors')
  const readOnly = useSetupReadOnly()
  const { data: planned } = useApi<Planned[]>('/connectors/planned')
  const { data: meta } = useApi<{ reset_enabled: boolean }>('/meta')
  // Which account the connect dialog is for; `account: null` adds another one to a work tool.
  const [editing, setEditing] = useState<{ c: Connector; account: Account | null } | null>(null)
  // The tab lives in the URL, so a refresh or a shared link opens the same one.
  const [params, setParams] = useSearchParams()
  const asked = params.get('tab') as Tab | null
  const tab: Tab = asked && TABS.includes(asked) ? asked : 'directory'
  if (loading && !data) return <PageSkeleton />
  if (error) return <ErrorNote message={error} />
  if (!data) return null

  const group = (people: boolean) => ({
    live: data.filter((c) => PEOPLE.has(c.category) === people),
    soon: (planned ?? []).filter((c) => PEOPLE.has(c.category) === people),
  })
  const directory = group(true)
  const tools = group(false)
  const linked = (cs: Connector[]) => cs.filter((c) => c.configured).length

  const options: { value: Tab; label: string }[] = [
    { value: 'directory', label: `Directory · ${linked(directory.live)}/${directory.live.length}` },
    { value: 'tools', label: `Work tools · ${linked(tools.live)}/${tools.live.length}` },
    { value: 'signin', label: 'Sign-in' },
    { value: 'alerts', label: 'Alerts' },
    ...(meta?.reset_enabled ? [{ value: 'sample' as const, label: 'Sample data' }] : []),
  ]

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Integrations" sub="Set up the organisation: who works here, the tools Handovers learns from, how people sign in, and how alerts reach them." />
      {readOnly && (
        <p role="status" className="flex items-center gap-2 rounded-[6px] bg-app px-4 py-2.5 text-[13px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)]">
          <Lock size={15} className="shrink-0" /> Viewing as a guest: look-only, so the demo stays as it is. Sign in as the platform admin to change anything.
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Segmented value={tab} onChange={(next) => setParams(next === 'directory' ? {} : { tab: next }, { preventScrollReset: true })} options={options} />
        <p className="flex items-center gap-1.5 text-[13px] text-ink-3">
          <Lock size={14} /> Credentials are encrypted and never shown again in full.
        </p>
      </div>
      {tab === 'directory' && (
        <ConnectorGrid intro="Who works here, their roles and managers, and who has left. Connect one first: it also signs people in." {...directory} onChanged={reload} onEdit={(c) => setEditing({ c, account: c.accounts[0] })} />
      )}
      {tab === 'tools' && (
        <ConnectorGrid intro="Where the work happens: decisions, code, tickets, documents and customers." {...tools} onChanged={reload} onEdit={(c, account) => setEditing({ c, account })} />
      )}
      {tab === 'signin' && <SignInSettings />}
      {tab === 'alerts' && <AlertDelivery />}
      {tab === 'sample' && meta?.reset_enabled && <SampleCompany />}
      {editing && (
        <ConnectModal
          c={editing.c}
          account={editing.account}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

/** Demo deployments only: reload the synthetic company (clears handovers and uploads). */
function SampleCompany() {
  const [busy, setBusy] = useState(false)
  const readOnly = useSetupReadOnly()

  async function reset() {
    if (!confirm('Reload the Northwind sample data? Handovers and uploads are cleared.')) return
    setBusy(true)
    await api.post('/demo/reset')
    window.location.assign(APP_BASE)
  }

  return (
    <section className="flex max-w-[560px] flex-col gap-3 rounded-[6px] bg-page p-5 shadow-card">
      <h2 className="text-[15px] font-semibold">Northwind sample company</h2>
      <p className="text-[14px] text-ink-2">Synthetic people and work for demos. Reloading puts it back as it was: handovers and uploads made since are cleared.</p>
      <div>
        <Button variant="secondary" onClick={() => void reset()} disabled={busy || readOnly} title={readOnly ? READ_ONLY_HINT : undefined}>
          {busy ? 'Reloading' : 'Reload sample data'}
        </Button>
      </div>
    </section>
  )
}

function ConnectorGrid({
  intro,
  live,
  soon,
  onChanged,
  onEdit,
}: {
  intro: string
  live: Connector[]
  soon: Planned[]
  onChanged: () => void
  /** Open the connect dialog for an account, or for a new one (`null`, work tools). */
  onEdit: (c: Connector, account: Account | null) => void
}) {
  return (
    <section className="flex flex-col gap-4">
      <p className="text-[14px] text-ink-3">{intro}</p>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {live.map((c) =>
          c.exclusive ? (
            <ConnectorCard
              key={c.id}
              c={c}
              activeOther={live.find((o) => o.id !== c.id && o.state?.active)?.name}
              onChanged={onChanged}
              onEdit={() => onEdit(c, c.accounts[0])}
            />
          ) : (
            <ToolCard key={c.id} c={c} onChanged={onChanged} onEdit={(account) => onEdit(c, account)} />
          ),
        )}
      </ul>
      {soon.length > 0 && <ComingSoon items={soon.map((p) => ({ ...p, label: CATEGORY[p.category] ?? p.category }))} />}
    </section>
  )
}

/** A work tool and every account connected for it, each with the teams it serves. */
function ToolCard({ c, onChanged, onEdit }: { c: Connector; onChanged: () => void; onEdit: (account: Account | null) => void }) {
  const readOnly = useSetupReadOnly()
  const lock = readOnly ? READ_ONLY_HINT : undefined
  const linked = c.accounts.filter((a) => a.configured)
  // Adding to a platform whose first account is free fills that one in, keeping its plain id.
  const add = () => onEdit(c.accounts[0].configured ? null : c.accounts[0])

  return (
    <li className="flex flex-col gap-3 rounded-[6px] bg-page p-4 shadow-card">
      <div className="flex items-start gap-3">
        <PlatformLogo id={c.id} name={c.name} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold">{c.name}</p>
          <p className="text-[12px] text-ink-3">{CATEGORY[c.category] ?? c.category}</p>
        </div>
        {linked.length ? <Chip tone="ok">{linked.length === 1 ? '1 account' : `${linked.length} accounts`}</Chip> : <Chip>Not connected</Chip>}
      </div>
      <p className="text-[13px] text-ink-2">{BRINGS[c.id]}</p>
      {linked.length > 0 && (
        <ul className="flex flex-col divide-y divide-line rounded-[6px] shadow-[inset_0_0_0_1px_var(--color-line)]">
          {linked.map((a) => (
            <AccountRow key={a.id} c={c} a={a} onChanged={onChanged} onEdit={() => onEdit(a)} />
          ))}
        </ul>
      )}
      <div className="mt-auto pt-1">
        <Button variant={linked.length ? 'secondary' : 'primary'} onClick={add} disabled={readOnly} title={lock}>
          {linked.length ? 'Add account' : 'Connect'}
        </Button>
      </div>
    </li>
  )
}

function AccountRow({ c, a, onChanged, onEdit }: { c: Connector; a: Account; onChanged: () => void; onEdit: () => void }) {
  const readOnly = useSetupReadOnly()
  const lock = readOnly ? READ_ONLY_HINT : undefined
  const [busy, setBusy] = useState<'sync' | 'test' | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const s = a.state

  async function act(kind: 'sync' | 'test') {
    setBusy(kind)
    setFailure(null)
    try {
      const path = `/connectors/${encodeURIComponent(a.id)}`
      // Test with no values: the saved settings, and the result is kept for this account.
      if (kind === 'test') await api.post(`${path}/test`, { values: {} })
      else await api.post(`${path}/sync`)
      onChanged()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'That did not work')
    } finally {
      setBusy(null)
    }
  }

  return (
    <li className="flex flex-col gap-1.5 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[14px] font-medium">{a.label ?? c.name}</span>
        {a.teams.map((t) => (
          <Chip key={t.id}>{t.name}</Chip>
        ))}
        {s?.status === 'error' && <Chip tone="risk">Sync failed</Chip>}
      </div>
      <p className="text-[12px] text-ink-3">
        {s?.last_sync ? `Last sync ${date(s.last_sync, true)}` : 'Not synced yet'}
        {s?.last_sync && s.status !== 'error' ? ` · ${s.sources ?? 0} records, ${s.facts ?? 0} facts` : ''}
        {s?.tested_at ? ` · ${s.test_ok ? 'connection works' : 'test failed'}` : ''}
      </p>
      <div className="flex flex-wrap gap-1.5">
        <Button variant="secondary" onClick={() => void act('sync')} disabled={busy !== null || readOnly} title={lock}>
          <ArrowsClockwise size={15} className={busy === 'sync' ? 'animate-spin' : ''} />
          {busy === 'sync' ? 'Syncing' : 'Sync'}
        </Button>
        <Button variant="ghost" onClick={() => void act('test')} disabled={busy !== null || readOnly} title={lock}>
          {busy === 'test' ? 'Testing' : 'Test'}
        </Button>
        <Button variant="ghost" onClick={onEdit} disabled={readOnly} title={lock}>
          Settings
        </Button>
      </div>
      {(failure || (s?.status === 'error' && s.error) || (s?.tested_at && !s.test_ok && s.test_message)) && (
        <p className="text-[12px] text-risk-text">{failure ?? (s?.status === 'error' ? s?.error : s?.test_message)}</p>
      )}
    </li>
  )
}

function ConnectorCard({
  c,
  activeOther,
  onChanged,
  onEdit,
}: {
  c: Connector
  /** The other connector active in this category, if any: making this one active replaces it. */
  activeOther?: string
  onChanged: () => void
  onEdit: () => void
}) {
  const readOnly = useSetupReadOnly()
  const [busy, setBusy] = useState<'sync' | 'test' | 'activate' | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const s = c.state
  const active = !!s?.active
  const path = `/connectors/${encodeURIComponent(c.id)}`
  const lock = readOnly ? READ_ONLY_HINT : undefined

  async function act(kind: 'sync' | 'test' | 'activate' | 'deactivate') {
    if (kind === 'activate' && activeOther && !confirm(`Make ${c.name} the active directory? ${activeOther} becomes inactive; its settings are kept.`)) return
    setBusy(kind === 'deactivate' ? 'activate' : kind)
    setFailure(null)
    try {
      // Test with no values: the saved settings, and the result is kept for this card.
      if (kind === 'test') await api.post(`${path}/test`, { values: {} })
      else await api.post(`${path}/${kind}`)
      onChanged()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'That did not work')
    } finally {
      setBusy(null)
    }
  }

  const status = !c.configured ? (
    <Chip>Not connected</Chip>
  ) : c.exclusive ? (
    active ? <Chip tone="ok">Active</Chip> : <Chip>Inactive</Chip>
  ) : s?.status === 'error' ? (
    <Chip tone="risk">Sync failed</Chip>
  ) : s?.last_sync ? (
    <Chip tone="ok">Connected</Chip>
  ) : (
    <Chip tone="accent">Ready to sync</Chip>
  )

  const counts = s
    ? [
        s.people ? `${s.people} people` : null,
        s.sources ? `${s.sources} records` : null,
        s.facts ? `${s.facts} facts` : null,
        s.review ? `${s.review} to review` : null,
      ].filter(Boolean)
    : []

  return (
    <li className="flex flex-col gap-3 rounded-[6px] bg-page p-4 shadow-card">
      <div className="flex items-start gap-3">
        <PlatformLogo id={c.id} name={c.name} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold">{c.name}</p>
          <p className="text-[12px] text-ink-3">{CATEGORY[c.category] ?? c.category}</p>
        </div>
        {status}
      </div>
      <p className="text-[13px] text-ink-2">{BRINGS[c.id]}</p>
      <dl className="flex flex-col gap-0.5 text-[12px] text-ink-3">
        {c.configured && c.exclusive && !active && (
          <dd>{activeOther ? `Settings kept. ${activeOther} is the active directory.` : 'Settings kept. Make it active to sync people.'}</dd>
        )}
        {s?.last_sync && (
          <dd className={s.status === 'error' ? 'text-risk-text' : undefined}>
            {s.status === 'error' ? 'Last sync failed' : 'Last sync'} {date(s.last_sync, true)}
            {s.status !== 'error' && (counts.length ? ` · ${counts.join(', ')}` : ' · nothing new')}
          </dd>
        )}
        {s?.tested_at && (
          <dd className={s.test_ok ? undefined : 'text-risk-text'}>
            {s.test_ok ? 'Connection works' : 'Test failed'} · tested {date(s.tested_at, true)}
            {!s.test_ok && s.test_message ? `: ${s.test_message}` : ''}
          </dd>
        )}
      </dl>
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-1">
        {c.configured ? (
          <>
            {c.exclusive && !active && (
              <Button onClick={() => void act('activate')} disabled={busy !== null || readOnly} title={lock}>
                {busy === 'activate' ? 'Switching' : 'Make active'}
              </Button>
            )}
            {(!c.exclusive || active) && (
              <Button
                variant="secondary"
                onClick={() => void act('sync')}
                disabled={busy !== null || readOnly}
                title={lock}
              >
                <ArrowsClockwise size={16} className={busy === 'sync' ? 'animate-spin' : ''} />
                {busy === 'sync' ? 'Syncing' : 'Sync now'}
              </Button>
            )}
            <Button variant="ghost" onClick={() => void act('test')} disabled={busy !== null || readOnly} title={lock}>
              {busy === 'test' ? 'Testing' : 'Test'}
            </Button>
            <Button variant="ghost" onClick={onEdit} disabled={readOnly} title={lock}>
              Settings
            </Button>
            {c.exclusive && active && (
              <Button variant="ghost" onClick={() => void act('deactivate')} disabled={busy !== null || readOnly} title={lock}>
                Deactivate
              </Button>
            )}
          </>
        ) : (
          <Button onClick={onEdit} disabled={readOnly} title={readOnly ? READ_ONLY_HINT : undefined}>
            Connect
          </Button>
        )}
      </div>
      {(failure || (s?.status === 'error' && s.error)) && <p className="text-[13px] text-risk-text">{failure ?? s?.error}</p>}
    </li>
  )
}

function ConnectModal({ c, account, onClose, onSaved }: { c: Connector; account: Account | null; onClose: () => void; onSaved: () => void }) {
  // A new account (work tools) starts from an empty form, never another account's values.
  const fields = account ? account.fields : c.fields.map((f) => ({ ...f, set: false, value: '', source: null }))
  const id = account?.id ?? `${c.id}:new`
  const configured = account?.configured ?? false
  const tool = !c.exclusive
  // Plain fields start with their current value; secrets start empty (blank keeps the stored one).
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(fields.map((f) => [f.key, f.secret ? '' : f.value])))
  const [label, setLabel] = useState(account?.label ?? '')
  const [teams, setTeams] = useState<string[]>(() => (account?.teams ?? []).map((t) => t.id))
  const { data: allTeams } = useApi<Team[]>(tool ? '/connectors/teams' : null)
  const [busy, setBusy] = useState<'save' | 'remove' | 'test' | null>(null)
  const [test, setTest] = useState<{ ok: boolean; message: string } | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const fromApp = fields.some((f) => f.source === 'app')
  // A second account of a tool needs a name to tell it apart; the first may stay unnamed.
  const needsLabel = tool && !account

  async function save(syncAfter: boolean) {
    if (needsLabel && !label.trim()) {
      setFailure('Name the account, e.g. Sales Jira.')
      return
    }
    setBusy('save')
    setFailure(null)
    try {
      let saved = id
      if (!account) {
        saved = (await api.post<{ id: string }>(`/connectors/${encodeURIComponent(c.id)}/accounts`, { values, label, teams })).id
      } else {
        await api.put(`/connectors/${encodeURIComponent(id)}/config`, tool ? { values, label: label.trim() || null, teams } : { values })
      }
      if (syncAfter) await api.post(`/connectors/${encodeURIComponent(saved)}/sync`)
      onSaved()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Could not save')
      setBusy(null)
    }
  }

  /** One read-only call to the platform with the values in the form; nothing is saved. */
  async function testConnection() {
    setBusy('test')
    setFailure(null)
    setTest(null)
    try {
      setTest(await api.post<{ ok: boolean; message: string }>(`/connectors/${encodeURIComponent(id)}/test`, { values }))
    } catch (e) {
      setTest({ ok: false, message: e instanceof Error ? e.message : 'Test failed' })
    } finally {
      setBusy(null)
    }
  }

  async function remove() {
    setBusy('remove')
    try {
      await api.del(`/connectors/${encodeURIComponent(id)}/config`)
      onSaved()
    } catch (e) {
      setFailure(e instanceof Error ? e.message : 'Could not disconnect')
      setBusy(null)
    }
  }

  return (
    <Modal
      title={
        <span className="flex items-center gap-2.5">
          <PlatformMark id={c.id} name={c.name} /> {configured ? `${account?.label ?? c.name} settings` : account ? `Connect ${c.name}` : `Add a ${c.name} account`}
        </span>
      }
      description={BRINGS[c.id]}
      onClose={onClose}
      footer={
        <>
          {configured && (fromApp || (account && account.id !== c.id)) && (
            <Button variant="ghost" className="mr-auto text-risk-text" onClick={() => void remove()} disabled={busy !== null}>
              {busy === 'remove' ? 'Disconnecting' : 'Disconnect'}
            </Button>
          )}
          <Button variant="secondary" onClick={onClose} disabled={busy !== null}>
            Cancel
          </Button>
          <Button variant="secondary" onClick={() => void testConnection()} disabled={busy !== null}>
            {busy === 'test' ? 'Testing' : 'Test connection'}
          </Button>
          <Button onClick={() => void save(true)} disabled={busy !== null}>
            {busy === 'save' ? 'Saving' : configured ? 'Save and sync' : 'Connect and sync'}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          void save(true)
        }}
      >
        {tool && (
          <>
            <label className="flex flex-col gap-1.5">
              <span className="text-[14px] font-medium">Account name{needsLabel ? '' : ' (optional)'}</span>
              <Input autoFocus value={label} placeholder={`e.g. Sales ${c.name}`} onChange={(e) => setLabel(e.target.value)} />
            </label>
            {allTeams && allTeams.length > 0 && (
              <fieldset className="flex flex-col gap-1.5">
                <legend className="mb-1.5 text-[14px] font-medium">Teams it serves</legend>
                <div className="flex flex-wrap gap-1.5">
                  {allTeams.map((t) => {
                    const on = teams.includes(t.id)
                    return (
                      <button
                        key={t.id}
                        type="button"
                        aria-pressed={on}
                        onClick={() => setTeams((cur) => (on ? cur.filter((x) => x !== t.id) : [...cur, t.id]))}
                        className={`rounded-[3px] px-2.5 py-1 text-[12.5px] transition-colors ${on ? 'bg-accent-fill text-white' : 'bg-app text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)] hover:text-ink'}`}
                      >
                        {t.name}
                      </button>
                    )
                  })}
                </div>
                <span className="text-[13px] text-ink-3">Its records count as these teams&apos; work. Who can see them does not change.</span>
              </fieldset>
            )}
          </>
        )}
        {fields.map((f, i) => (
          <label key={f.key} className="flex flex-col gap-1.5">
            <span className="text-[14px] font-medium">{f.label}</span>
            <Input
              autoFocus={!tool && i === 0}
              type={f.secret ? 'password' : 'text'}
              autoComplete="off"
              spellCheck={false}
              value={values[f.key] ?? ''}
              placeholder={f.secret && f.set ? `${f.value} (leave blank to keep)` : f.placeholder}
              onChange={(e) => {
                setValues((v) => ({ ...v, [f.key]: e.target.value }))
                setTest(null) // a result is only valid for the values it tested
              }}
            />
            {f.hint && <span className="text-[13px] text-ink-3">{f.hint}</span>}
            {f.source === 'server' && <span className="text-[13px] text-ink-3">Currently set on the server; a value here replaces it.</span>}
          </label>
        ))}
        {test && (
          <p role="status" className={`rounded-[6px] px-4 py-3 text-[14px] ${test.ok ? 'bg-ok-soft text-ok-text' : 'bg-risk-soft text-risk-text'}`}>
            {test.ok ? 'Connection works. ' : 'Connection failed. '}
            {test.message}
          </p>
        )}
        {failure && <p className="text-[13px] text-risk-text">{failure}</p>}
        <button type="submit" hidden />
      </form>
    </Modal>
  )
}
