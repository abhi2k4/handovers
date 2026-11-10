import { APP_BASE } from '../app/base'
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { useApi } from '../hooks/useApi'
import { ViewAsContext, useViewAs, type AuthConfig, type Me, type Persona, type Session } from '../hooks/useViewAs'
import { api } from '../lib/api'
import { useDataVersion } from '../lib/freshness'
import { getViewAs, setViewAs } from '../lib/viewAs'
import { Check, ChevronsUpDown, SignOut, Users } from './icons'
import { Avatar, Button, Modal } from './ui'

/**
 * Who is using the app. A signed-in session (Keycloak) wins: the persona is then that person and the
 * View-as switcher is hidden. Without one, guests pick a demo persona ("View as"), as before.
 */
export function ViewAsProvider({ children }: { children: ReactNode }) {
  const { data: auth } = useApi<AuthConfig>('/auth/config')
  const { data: session, loading: sessionLoading } = useApi<Session | null>('/auth/session')
  const [chosen, setState] = useState(getViewAs())
  const persona = session?.employee ?? chosen
  const version = useDataVersion()
  // The query string re-keys the request when the persona changes or data changed (the header
  // carries the persona), so homes built from `me` (leaving, managing) are fresh after an action.
  const { data, error: meError } = useApi<Me | null>(`/me?as=${encodeURIComponent(persona)}&v=${version}`)
  const me = persona && data?.id === persona ? data : null

  useEffect(() => {
    // Signed in: stop sending the demo header (the backend ignores it anyway).
    if (session) setViewAs('')
  }, [session])

  const setPersona = (id: string) => {
    setViewAs(id)
    setState(id)
  }
  // Unrestricted mode (no persona) sees everything, as before.
  const has = (role: string) => !persona || (me?.roles.includes(role) ?? false)

  return (
    <ViewAsContext.Provider value={{ persona, setPersona, me, meError: me ? null : meError, has, session: session ?? null, auth: auth ?? null, sessionLoading }}>
      {children}
    </ViewAsContext.Provider>
  )
}

/** Bottom of the sidebar: the signed-in person with Sign out, or the guest "View as" picker. */
export function IdentityPanel() {
  const { session, auth } = useViewAs()
  return session ? <SignedIn /> : <ViewAsSwitcher signIn={auth?.available ?? false} />
}

function SignedIn() {
  const { me, session } = useViewAs()
  const [busy, setBusy] = useState(false)

  async function signOut() {
    setBusy(true)
    let logoutUrl: string | null = null
    try {
      logoutUrl = (await api.post<{ logout_url: string | null }>('/auth/logout')).logout_url
    } catch {
      // The session may already be gone; go to the sign-in page either way.
    }
    // Keycloak ends its own session too, then returns to /login.
    window.location.assign(logoutUrl ?? `${APP_BASE}/login`)
  }

  return (
    <div className="flex items-center gap-2.5 px-2 py-1">
      <Avatar name={session?.name ?? ''} size={32} />
      <span className="min-w-0 flex-1 leading-tight">
        <span className="block truncate text-[14px] font-medium text-ink">{session?.name}</span>
        <span className="block truncate text-[12px] text-ink-3">{me?.title ?? session?.email}</span>
      </span>
      <button
        onClick={() => void signOut()}
        disabled={busy}
        aria-label="Sign out"
        title="Sign out"
        className="flex size-8 shrink-0 items-center justify-center rounded-[4px] text-ink-3 transition-colors hover:bg-hover hover:text-ink disabled:opacity-50"
      >
        <SignOut size={16} />
      </button>
    </div>
  )
}

/** "View as" switcher: demo identities, each seeing what that person would see. Opens upward from the sidebar foot. */
function ViewAsSwitcher({ signIn = false }: { signIn?: boolean }) {
  const { persona, setPersona, me } = useViewAs()
  const { data: personas } = useApi<Persona[]>('/personas')
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const current = personas?.find((p) => p.id === persona)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => root.current && !root.current.contains(e.target as Node) && setOpen(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  function pick(id: string) {
    setOpen(false)
    if (id === persona) return
    setPersona(id)
    navigate('/')
  }

  // With sign-in on, no person means look-only (the API refuses changes).
  const lookOnly = useViewAs().auth?.sso ?? false
  const options: { id: string; name: string; sub: string }[] = [
    { id: '', name: 'Everyone', sub: lookOnly ? 'Look only' : 'No restrictions' },
    ...(personas ?? []).map((p) => ({ id: p.id, name: p.name, sub: p.label })),
  ]

  return (
    <div ref={root} className="relative">
      {open && (
        <div
          role="listbox"
          aria-label="View as"
          className="absolute right-0 bottom-[calc(100%+6px)] left-0 z-50 max-h-[min(440px,70dvh)] overflow-y-auto rounded-[6px] bg-page p-1.5 shadow-[0_12px_32px_-8px_rgba(15,27,45,0.24),0_0_0_1px_var(--color-line)] [animation:pop-in_140ms_ease-out]"
        >
          <div className="flex items-center justify-between px-2 pt-1 pb-1.5 text-[12px] font-medium text-ink-3">
            <span>View the app as</span>
            {signIn && (
              <Link to="/login" className="text-accent hover:underline">
                Sign in
              </Link>
            )}
          </div>
          {options.map((o) => {
            const active = o.id === persona
            return (
              <button
                key={o.id || 'everyone'}
                role="option"
                aria-selected={active}
                onClick={() => pick(o.id)}
                className={`flex w-full items-center gap-2.5 rounded-[4px] px-2 py-1.5 text-left transition-colors duration-100 ${active ? 'bg-accent-soft' : 'hover:bg-hover'}`}
              >
                {o.id ? <Avatar name={o.name} size={28} /> : <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-hover text-ink-3"><Users size={15} /></span>}
                <span className="min-w-0 flex-1">
                  <span className={`block truncate text-[13px] font-medium ${active ? 'text-accent' : 'text-ink'}`}>{o.name}</span>
                  <span className="block truncate text-[12px] text-ink-3">{o.sub}</span>
                </span>
                {active && <Check size={14} weight="bold" className="shrink-0 text-accent" />}
              </button>
            )
          })}
        </div>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex w-full items-center gap-2.5 rounded-[6px] px-2 py-1.5 text-left transition-colors duration-150 ${open ? 'bg-hover' : 'hover:bg-hover'}`}
      >
        {me ? <Avatar name={me.name} size={32} /> : <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-hover text-ink-3"><Users size={16} /></span>}
        <span className="min-w-0 flex-1 leading-tight">
          <span className="block truncate text-[14px] font-medium text-ink">{me?.name ?? current?.name ?? 'Everyone'}</span>
          <span className="block truncate text-[12px] text-ink-3">{current ? `${current.label} · guest view` : lookOnly ? 'Guest · look only' : 'Guest · no restrictions'}</span>
        </span>
        <ChevronsUpDown size={15} className="shrink-0 text-ink-3" />
      </button>
    </div>
  )
}

const LOOK_ONLY = 'handovers.lookOnly'

function lookingOnly(): boolean {
  try {
    return sessionStorage.getItem(LOOK_ONLY) === '1'
  } catch {
    return false
  }
}

/**
 * First visit to a deployment with sign-in on and guests allowed: pick who to explore as. Without
 * a person (or a sign-in) the app is look-only, so the first click on any action would fail.
 */
export function FirstVisitPicker({ paused }: { paused: boolean }) {
  const { persona, setPersona, session, auth, sessionLoading } = useViewAs()
  const [dismissed, setDismissed] = useState(lookingOnly)
  const needed = !!auth?.sso && auth.guest && !sessionLoading && !session && !persona && !dismissed
  const { data: personas } = useApi<Persona[]>(needed ? '/personas' : null)
  const navigate = useNavigate()
  if (!needed || paused) return null

  function lookAround() {
    try {
      sessionStorage.setItem(LOOK_ONLY, '1')
    } catch {
      // storage unavailable: the choice lasts for this page only
    }
    setDismissed(true)
  }

  return (
    <Modal
      title="Explore Handovers as…"
      description="Each person sees what they would at work: their own home, alerts and actions."
      onClose={lookAround}
      footer={
        <>
          {auth?.available && (
            <Link to="/login" className="mr-auto text-[14px] font-medium text-accent hover:underline">
              Sign in instead
            </Link>
          )}
          <Button variant="ghost" onClick={lookAround}>
            Just look around
          </Button>
        </>
      }
    >
      {!personas ? (
        <p className="text-[14px] text-ink-3">Loading people…</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {personas.map((p) => (
            <li key={p.id}>
              <button
                onClick={() => {
                  setPersona(p.id)
                  navigate('/')
                }}
                className="flex w-full items-center gap-3 rounded-[6px] px-2.5 py-2 text-left transition-colors hover:bg-hover focus-visible:bg-hover"
              >
                <Avatar name={p.name} size={32} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14px] font-medium text-ink">{p.name}</span>
                  <span className="block truncate text-[12.5px] text-ink-3">{p.title}</span>
                </span>
                <span className="shrink-0 text-[12.5px] font-medium text-ink-2">{p.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}
