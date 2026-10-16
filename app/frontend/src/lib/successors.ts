import type { PersonRow } from '../types/api'

/**
 * Who can take over a leaver's work: not the leaver, not someone already leaving, not someone who
 * has left (the backend enforces the same rule). Same team first; other teams are allowed but the
 * server asks for confirmation (`useConfirmable`).
 */
export function successorOptions(people: PersonRow[], leaver: { id: string; team?: string | null; team_id?: string | null } | null) {
  const ok = people.filter((p) => p.id !== leaver?.id && p.status !== 'departed' && !p.handover_id)
  const same = (p: PersonRow) => !!leaver && (leaver.team_id ? p.team_id === leaver.team_id : p.team === leaver.team)
  return [...ok.filter(same), ...ok.filter((p) => !same(p))].map((p) => ({ ...p, sameTeam: same(p) }))
}
