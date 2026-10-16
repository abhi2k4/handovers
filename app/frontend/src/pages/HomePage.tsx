import { Navigate } from 'react-router'
import { useViewAs } from '../hooks/useViewAs'
import { Loading } from '../components/ui'
import { EmployeeHome } from './home/EmployeeHome'
import { LeadershipHome } from './home/LeadershipHome'
import { LeaverHome } from './home/LeaverHome'
import { ManagerHome } from './home/ManagerHome'
import { SuccessorHome } from './home/SuccessorHome'
import { OverviewPage } from './OverviewPage'
import { PersonPage } from './PersonPage'

/** One app, a different home per person (docs/product-strategy.md section 10.2). */
export function HomePage() {
  const { persona, me } = useViewAs()
  if (!persona) return <OverviewPage />
  if (!me) return <Loading />
  switch (me.home) {
    case 'leaver':
      return <LeaverHome me={me} />
    case 'successor':
      return <SuccessorHome me={me} />
    case 'manager':
      return <ManagerHome me={me} />
    case 'overview':
      return <OverviewPage />
    case 'leadership':
      return <LeadershipHome me={me} />
    case 'platform':
      // The platform admin sets up the organisation; they see no people or handovers.
      return <Navigate to="/integrations" replace />
    default:
      return <EmployeeHome me={me} />
  }
}

/** "My memory": your own person page, written to you. Without a persona there is no "you". */
export function MyMemoryPage() {
  const { persona, me } = useViewAs()
  if (!persona) return <Navigate to="/people" replace />
  if (!me) return <Loading />
  return <PersonPage self={me.id} />
}
