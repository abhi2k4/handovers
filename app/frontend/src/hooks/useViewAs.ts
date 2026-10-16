import { createContext, useContext } from 'react'

export interface HandoverSummary {
  id: string
  status: string
  effective_at: number | null
  employee_id: string
  employee: string
  title: string | null
  manager_id: string | null
  manager: string | null
  successor_id: string | null
  successor: string | null
}

export type Home = 'leaver' | 'successor' | 'overview' | 'leadership' | 'manager' | 'employee' | 'platform'

export interface Me {
  id: string
  name: string
  title: string
  team: string | null
  roles: string[]
  home: Home
  reports: string[]
  leaving: HandoverSummary[]
  succeeding: HandoverSummary[]
  managing: HandoverSummary[]
  /** Chosen in View as, not signed in: setup pages are look-only. */
  guest: boolean
}

export interface Persona {
  id: string
  name: string
  title: string
  label: string
}

/** The signed-in person (Keycloak session); null for guests. */
export interface Session {
  employee: string
  name: string
  email: string
}

/** What the login page offers (GET /api/auth/config). */
export interface AuthConfig {
  sso: boolean
  /** Keycloak is configured and reachable right now. */
  available: boolean
  guest: boolean
  providers: { id: string; name: string }[]
}

interface ViewAsState {
  persona: string
  setPersona: (id: string) => void
  /** null when no persona is chosen (unrestricted demo mode). */
  me: Me | null
  has: (role: string) => boolean
  session: Session | null
  auth: AuthConfig | null
  sessionLoading: boolean
}


export const ViewAsContext = createContext<ViewAsState>({
  persona: '',
  setPersona: () => {},
  me: null,
  has: () => true,
  session: null,
  auth: null,
  sessionLoading: false,
})

export function useViewAs(): ViewAsState {
  return useContext(ViewAsContext)
}

/** Setup (integrations, sign-in, sample data) is look-only for a View-as guest: the demo stays seeded. */
export function useSetupReadOnly(): boolean {
  return useContext(ViewAsContext).me?.guest ?? false
}

export const READ_ONLY_HINT = 'Sign in as the platform admin to change this'
