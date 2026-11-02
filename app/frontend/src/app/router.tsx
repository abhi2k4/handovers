import { createBrowserRouter } from 'react-router'
import { APP_BASE } from './base'
import { AppLayout } from '../layouts/AppLayout'
import { AlertsPage } from '../pages/AlertsPage'
import { AskPage } from '../pages/AskPage'
import { HandoversPage } from '../pages/HandoversPage'
import { HomePage, MyMemoryPage } from '../pages/HomePage'
import { HandoverPage } from '../pages/handover/HandoverPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { PeoplePage } from '../pages/PeoplePage'
import { PersonPage } from '../pages/PersonPage'

// Pages most people open rarely (setup, HR tools, sign-in) load on demand, so the first screen
// downloads less. prefetchRarePages() fetches them in idle time, so opening one later is instant.
const rare = {
  accounts: () => import('../pages/AccountsPage').then((m) => ({ Component: m.AccountsPage })),
  insights: () => import('../pages/InsightsPage').then((m) => ({ Component: m.InsightsPage })),
  integrations: () => import('../pages/IntegrationsPage').then((m) => ({ Component: m.IntegrationsPage })),
  login: () => import('../pages/LoginPage').then((m) => ({ Component: m.LoginPage })),
  policy: () => import('../pages/PolicyPage').then((m) => ({ Component: m.PolicyPage })),
  sources: () => import('../pages/SourcesPage').then((m) => ({ Component: m.SourcesPage })),
}

export function prefetchRarePages(): void {
  Object.values(rare).forEach((load) => void load().catch(() => {}))
}

export const router = createBrowserRouter([
  { path: '/login', lazy: rare.login },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'insights', lazy: rare.insights },
      { path: 'accounts', lazy: rare.accounts },
      { path: 'me', element: <MyMemoryPage /> },
      { path: 'people', element: <PeoplePage /> },
      { path: 'people/:id', element: <PersonPage /> },
      { path: 'handovers', element: <HandoversPage /> },
      { path: 'handovers/:id', element: <HandoverPage /> },
      { path: 'ask', element: <AskPage /> },
      { path: 'alerts', element: <AlertsPage /> },
      { path: 'sources', lazy: rare.sources },
      { path: 'integrations', lazy: rare.integrations },
      { path: 'policy', lazy: rare.policy },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
], { basename: APP_BASE })
