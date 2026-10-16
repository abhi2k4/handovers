import '@fontsource-variable/geist'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { APP_BASE } from './app/base'
import { Root } from './Root'
import { applyTheme } from './lib/theme'
import './styles/index.css'

// Routes: "/" is the landing page; the app lives under /dashboard (react-router basename).
// Any other path is an older app link (/handovers/..., /login from Keycloak's logout): move it
// under /dashboard so shared links keep working.
const { pathname, search, hash } = window.location
const inApp = pathname === APP_BASE || pathname.startsWith(`${APP_BASE}/`)

if (pathname !== '/' && !inApp) {
  window.location.replace(`${APP_BASE}${pathname}${search}${hash}`)
} else {
  // The app's light or dark theme, set before the first paint; the landing page keeps its own look.
  if (inApp) applyTheme()
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <Root inApp={inApp} />
    </StrictMode>,
  )
}
