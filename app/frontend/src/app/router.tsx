import { createBrowserRouter } from 'react-router'
import { APP_BASE } from './base'
import { AppLayout } from '../layouts/AppLayout'
import { AccountsPage } from '../pages/AccountsPage'
import { AlertsPage } from '../pages/AlertsPage'
import { AskPage } from '../pages/AskPage'
import { HandoversPage } from '../pages/HandoversPage'
import { HomePage, MyMemoryPage } from '../pages/HomePage'
import { HandoverPage } from '../pages/handover/HandoverPage'
import { InsightsPage } from '../pages/InsightsPage'
import { IntegrationsPage } from '../pages/IntegrationsPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { PeoplePage } from '../pages/PeoplePage'
import { PersonPage } from '../pages/PersonPage'
import { PolicyPage } from '../pages/PolicyPage'
import { SourcesPage } from '../pages/SourcesPage'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'insights', element: <InsightsPage /> },
      { path: 'accounts', element: <AccountsPage /> },
      { path: 'me', element: <MyMemoryPage /> },
      { path: 'people', element: <PeoplePage /> },
      { path: 'people/:id', element: <PersonPage /> },
      { path: 'handovers', element: <HandoversPage /> },
      { path: 'handovers/:id', element: <HandoverPage /> },
      { path: 'ask', element: <AskPage /> },
      { path: 'alerts', element: <AlertsPage /> },
      { path: 'sources', element: <SourcesPage /> },
      { path: 'integrations', element: <IntegrationsPage /> },
      { path: 'policy', element: <PolicyPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
], { basename: APP_BASE })
