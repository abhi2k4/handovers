import { lazy, Suspense } from 'react'

const Landing = lazy(() => import('./landing/Landing'))
const App = lazy(() => import('./app/App'))

/** "/" is the landing page; the app (and its router) lives under /dashboard. */
export function Root({ inApp }: { inApp: boolean }) {
  return <Suspense fallback={null}>{inApp ? <App /> : <Landing />}</Suspense>
}
