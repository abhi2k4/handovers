import type { ComponentType } from 'react'
import { ArrowRightLeft, BarChart3, Bell, Brain, Database, KeyRound, LayoutGrid, ListChecks, MessageSquareText, PlugsConnected, Users } from '../components/icons'
import { useViewAs } from '../hooks/useViewAs'

/* The app's pages, in sidebar order. The sidebar and the ⌘K menu both list them through useNav(),
   so nobody is offered a page their role cannot open. */

export const GROUPS = ['You', 'Organisation', 'Data'] as const

type Icon = ComponentType<{ size?: number; weight?: 'regular' | 'duotone'; className?: string }>

// `roles`: who sees the item when a "View as" persona is chosen (any of them). No `roles` = everyone.
export interface NavItem {
  to: string
  label: string
  icon: Icon
  end?: boolean
  count?: 'handovers' | 'review' | 'alerts'
  roles?: string[]
  persona?: boolean
  group: (typeof GROUPS)[number]
}

const nav: NavItem[] = [
  { to: '/', label: 'Home', icon: LayoutGrid, end: true, group: 'You' },
  { to: '/ask', label: 'Ask', icon: MessageSquareText, group: 'You' },
  { to: '/me', label: 'My memory', icon: Brain, persona: true, group: 'You' },
  { to: '/alerts', label: 'Alerts', icon: Bell, count: 'alerts', persona: true, group: 'You' },
  { to: '/handovers', label: 'Handovers', icon: ArrowRightLeft, count: 'handovers', roles: ['hr', 'manager'], group: 'Organisation' },
  { to: '/people', label: 'People', icon: Users, roles: ['hr', 'exec', 'manager'], group: 'Organisation' },
  { to: '/insights', label: 'Insights', icon: BarChart3, roles: ['hr', 'exec'], group: 'Organisation' },
  { to: '/accounts', label: 'Accounts', icon: KeyRound, roles: ['it'], group: 'Organisation' },
  { to: '/sources', label: 'Sources', icon: Database, count: 'review', roles: ['hr'], group: 'Data' },
  { to: '/policy', label: 'Policies', icon: ListChecks, roles: ['hr', 'platform_admin'], group: 'Data' },
  { to: '/integrations', label: 'Integrations', icon: PlugsConnected, roles: ['platform_admin'], group: 'Data' },
]

/** The pages this person may open. The platform admin is not an employee: Integrations only. */
export function useNav(): NavItem[] {
  const { persona, me, has } = useViewAs()
  if (me?.roles.includes('platform_admin')) return nav.filter((n) => n.roles?.includes('platform_admin'))
  return nav.filter((n) => (n.persona ? !!persona : !n.roles || n.roles.some(has)))
}
