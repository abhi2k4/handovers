// HR approves or rejects a proposed account handover.
MATCH (h:Handover)-[:HAS_REASSIGNMENT]->(r:Reassignment {id: $id, status: 'proposed'})-[:OF]->(a:Account)
MATCH (r)-[:TO]->(to:Employee)
SET r.status = $status, r.decided_by = $by, r.decided_at = $now, r.decision_note = $note
RETURN r.id AS id, h.id AS handover, a.id AS account, a.name AS account_name, to.id AS to,
       to.name AS to_name, r.status AS status
