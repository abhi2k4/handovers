import { Link, useSearchParams } from 'react-router'
import { useApi } from '../hooks/useApi'
import { PlatformMark } from '../components/PlatformLogo'
import type { AuthConfig } from '../hooks/useViewAs'

/** Sign in with the company's account, or explore the demo as a guest. */
export function LoginPage() {
  const [params] = useSearchParams()
  const { data: auth } = useApi<AuthConfig>('/auth/config')
  const error = params.get('error')
  const next = params.get('next') ?? '/'
  const href = (provider?: string) => `/api/auth/login?${new URLSearchParams({ ...(provider ? { provider } : {}), next })}`
  const option =
    'flex h-11 w-full items-center justify-center gap-2.5 rounded-[6px] bg-page text-[15px] font-medium text-ink shadow-[inset_0_0_0_1px_var(--color-control),0_1px_2px_rgba(15,27,45,0.05)] transition-colors hover:bg-hover'

  return (
    <div className="grid min-h-dvh bg-app lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-[#0f1b2d] p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="flex size-10 items-center justify-center rounded-[6px] bg-page">
            <img src="/logo-mark-alpha.png" alt="" className="h-6 w-auto" />
          </span>
          <span className="text-[19px] font-semibold tracking-[-0.02em]">Handovers</span>
        </div>
        <div className="max-w-[440px]">
          <h1 className="text-[34px] leading-[42px] font-semibold tracking-[-0.02em]">People leave. Their context shouldn&apos;t.</h1>
          <p className="mt-4 text-[16px] leading-6 text-white/70">
            Handovers learns who does what from the tools you already use, and makes sure nothing walks out the door when someone does.
          </p>
        </div>
        <p className="text-[13px] text-white/50">Built on FalkorDB, the graph behind every answer.</p>
        <div className="pointer-events-none absolute -right-24 -bottom-24 size-[420px] rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.35),transparent_65%)]" />
        <div className="pointer-events-none absolute top-24 -right-10 size-[260px] rounded-full bg-[radial-gradient(circle,rgba(56,176,152,0.28),transparent_65%)]" />
      </aside>

      <main className="flex items-center justify-center p-6">
        <div className="w-full max-w-[400px]">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <img src="/logo-mark-alpha.png" alt="" className="h-7 w-auto" />
            <span className="text-[18px] font-semibold tracking-[-0.02em]">Handovers</span>
          </div>
          <h2 className="text-[26px] leading-8 font-semibold tracking-[-0.02em]">Sign in</h2>
          <p className="mt-1.5 text-[15px] text-ink-2">Use your work account.</p>

          {error && (
            <p role="alert" className="mt-5 rounded-[6px] bg-risk-soft px-4 py-3 text-[14px] text-risk-text">
              {error}
            </p>
          )}

          <div className="mt-7 flex flex-col gap-3">
            {auth?.sso && auth.available ? (
              <>
                {auth.providers.map((p) => (
                  <a key={p.id} href={href(p.id)} className={option}>
                    <PlatformMark id={p.id} name={p.name} size={18} /> Continue with {p.name}
                  </a>
                ))}
                <a href={href()} className={option}>
                  Continue with email
                </a>
              </>
            ) : (
              <p className="rounded-[6px] bg-page px-4 py-3 text-[14px] text-ink-2 shadow-[inset_0_0_0_1px_var(--color-line)]">
                {auth?.sso ? 'Single sign-on (SSO) is not available on this server right now.' : 'Single sign-on (SSO) is not available on this server.'}
              </p>
            )}
          </div>

          {(auth?.guest ?? true) && (
            <>
              <div className="my-6 flex items-center gap-3 text-[13px] text-ink-3">
                <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
              </div>
              <Link to="/" className="flex h-11 w-full items-center justify-center rounded-[6px] text-[15px] font-medium text-accent transition-colors hover:bg-accent-soft">
                Explore the demo as a guest
              </Link>
              <p className="mt-2 text-center text-[13px] text-ink-3">Switch between Northwind&apos;s people to see what each one sees.</p>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
