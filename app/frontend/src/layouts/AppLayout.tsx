import { CircleHelp, Search } from '../components/icons'
import { useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Outlet, ScrollRestoration, useLocation } from 'react-router'
import { CommandMenu } from '../components/CommandMenu'
import { CopilotBar } from '../components/Copilot'
import { XrayButton } from '../components/Xray'
import { ThemeSwitch } from '../components/ThemeSwitch'
import { TechGraphButton } from '../components/TechGraph'
import { Tour } from '../components/Tour'
import { IdentityPanel, ViewAsProvider } from '../components/ViewAs'
import { useTour } from '../hooks/useTour'
import { useViewAs } from '../hooks/useViewAs'
import { Kbd } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { date } from '../lib/format'
import { GROUPS, useNav } from './nav'

interface Meta {
  company: string
  now: number
}

// Show the shortcut the way each platform writes it; the handler accepts both Cmd and Ctrl.
const isMac = /Mac|iPhone|iPad/.test(navigator.userAgent)
const searchShortcut = isMac ? '⌘K' : 'Ctrl K'

export function AppLayout() {
  return (
    <ViewAsProvider>
      <Shell />
    </ViewAsProvider>
  )
}

function Shell() {
  const { persona, me, session, auth, sessionLoading } = useViewAs()
  const tour = useTour()
  // The platform admin is not an employee: Integrations only, no people or work pages.
  const items = useNav()
  const { data: meta } = useApi<Meta>('/meta')
  const location = useLocation()
  const { data: handovers } = useApi<{ status: string }[]>(`/handovers?r=${location.pathname}`)
  const { data: review } = useApi<unknown[]>(`/review?r=${location.pathname}`)
  const { data: alerts } = useApi<{ acted: string | null }[]>(persona && !me?.roles.includes('platform_admin') ? `/alerts?r=${location.pathname}` : null)
  const counts = {
    handovers: (handovers ?? []).filter((h) => h.status !== 'transferred').length,
    review: review?.length ?? 0,
    alerts: (alerts ?? []).filter((a) => !a.acted).length,
  }
  const [menu, setMenu] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setMenu((m) => !m)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // Sign-in required (no guest access): send anyone without a session to the login page.
  if (auth?.sso && !auth.guest && !sessionLoading && !session) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-dvh bg-app">
      <aside className="sticky top-0 hidden h-dvh w-[240px] shrink-0 flex-col border-r border-line bg-app px-3.5 pt-4 pb-3 md:flex">
        <Link
          to="/"
          aria-label="Handovers: go to your home"
          className="mb-4 flex h-10 items-center gap-2.5 rounded-[4px] px-2 transition-colors duration-150 hover:bg-hover"
        >
          <img src="/logo-wobg.png" alt="" className="h-6 w-auto dark:box-content dark:rounded-[4px] dark:px-1 dark:py-0.5" />
          <span className="min-w-0 leading-tight">
            <span className="block text-[16px] font-semibold tracking-[-0.02em]">Handovers</span>
            {meta && (
              <span className="num block truncate text-[12px] text-ink-3">
                {meta.company} · {date(meta.now, true)}
              </span>
            )}
          </span>
        </Link>

        <button
          onClick={() => setMenu(true)}
          className="mb-4 flex h-8 items-center gap-2 rounded-[4px] bg-page px-2.5 text-[13px] text-ink-3 shadow-[inset_0_0_0_1px_var(--color-line)] transition-shadow duration-150 hover:text-ink-2 hover:shadow-[inset_0_0_0_1px_var(--color-control)]"
        >
          <Search size={16} />
          <span className="flex-1 text-left">Search</span>
          <Kbd>{searchShortcut}</Kbd>
        </button>

        {/* Scrolls on its own on short screens, so the footer (help, identity) stays in view. */}
        <nav className="-mx-1 flex min-h-0 flex-col gap-4 overflow-y-auto px-1">
          {GROUPS.map((g) => {
            const groupItems = items.filter((i) => i.group === g)
            if (!groupItems.length) return null
            return (
              <div key={g}>
                <div className="eyebrow mb-1.5 px-2.5">{g}</div>
                <div className="flex flex-col gap-0.5">
                  {groupItems.map(({ to, label, icon: Icon, end, count }) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={end}
                      className={({ isActive }) =>
                        `group relative flex h-8 items-center gap-2.5 rounded-[4px] px-2.5 text-[13.5px] transition-colors duration-150 ${
                          isActive
                            ? 'bg-page font-medium text-ink shadow-[inset_0_0_0_1px_var(--color-line)] before:absolute before:top-1.5 before:bottom-1.5 before:-left-[7px] before:w-[2px] before:rounded-[1px] before:bg-accent-fill'
                            : 'text-ink-2 hover:bg-hover hover:text-ink'
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Icon size={16} weight={isActive ? 'duotone' : 'regular'} className={isActive ? 'text-accent' : 'text-ink-3 group-hover:text-ink-2'} />
                          <span className="flex-1">{label}</span>
                          {count && counts[count] > 0 && (
                            <span className={`num min-w-5 rounded-[3px] px-1.5 text-center font-mono text-[11px] font-medium ${isActive ? 'bg-accent-soft text-accent' : 'bg-hover text-ink-2'}`}>{counts[count]}</span>
                          )}
                        </>
                      )}
                    </NavLink>
                  ))}
                </div>
              </div>
            )
          })}
        </nav>

        <div className="mt-auto flex flex-col gap-2.5 border-t border-line pt-2.5">
          <div className="-mx-1 flex items-center justify-between">
            <button
              onClick={tour.show}
              className="flex h-8 items-center gap-1.5 rounded-[4px] px-1.5 text-[13px] whitespace-nowrap text-ink-2 transition-colors duration-150 hover:bg-hover hover:text-ink"
            >
              <CircleHelp size={16} className="text-ink-3" />
              How it works
            </button>
            <TechGraphButton />
          </div>
          <IdentityPanel />
        </div>

      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <nav className="flex items-center gap-4 overflow-x-auto border-b border-line bg-page px-4 py-3 text-[14px] md:hidden">
          {items.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'font-medium text-ink' : 'text-ink-2')}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 bg-page">
          <div className="mx-auto w-full max-w-[1240px] px-5 py-8 md:px-10 md:py-10">
            {/* Full-width band so scrolled content never shows beside the bar. */}
            <div className="sticky top-0 z-30 -mx-5 -mt-8 mb-5 border-b border-line bg-page/90 px-5 pt-3 pb-3 backdrop-blur-md md:-mx-10 md:-mt-10 md:mb-6 md:px-10 md:pt-4">
              <div className="mx-auto flex w-full max-w-[860px] items-start gap-2">
                <CopilotBar key={`copilot-${persona}`} />
                <XrayButton />
                <ThemeSwitch />
              </div>
            </div>
            {/* Re-keyed per page: each screen fades up instead of swapping in place. */}
            <div key={`${persona}:${location.pathname}`} className="[animation:page-in_180ms_cubic-bezier(0.2,0.7,0.2,1)]">
              <Outlet />
            </div>
          </div>
        </main>
      </div>

      {/* New page: start at the top. Back/forward: return to where you were. Tabs opt out (preventScrollReset). */}
      <ScrollRestoration />
      {menu && <CommandMenu open onClose={() => setMenu(false)} />}
      <Tour open={tour.open} onClose={tour.hide} />
    </div>
  )
}
