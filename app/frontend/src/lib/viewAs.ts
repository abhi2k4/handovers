// Demo identity ("View as"). Sent to the API as the X-View-As header; the backend applies every
// access rule from it (app/backend/services/access.py). Not authentication: a Keycloak login
// replaces this later (docs/identity-and-access.md).

const KEY = 'handovers.viewAs'

export function getViewAs(): string {
  try {
    return localStorage.getItem(KEY) ?? ''
  } catch {
    return ''
  }
}

export function setViewAs(id: string): void {
  try {
    if (id) localStorage.setItem(KEY, id)
    else localStorage.removeItem(KEY)
  } catch {
    // storage unavailable (private mode): the choice lasts for this page only
  }
}
