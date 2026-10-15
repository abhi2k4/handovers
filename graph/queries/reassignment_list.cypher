// Account handovers proposed for a handover, newest first.
MATCH (:Handover {id: $handover})-[:HAS_REASSIGNMENT]->(r:Reassignment)-[:OF]->(a:Account)
MATCH (r)-[:TO]->(to:Employee)
RETURN r.id AS id, r.status AS status, a.id AS account, a.name AS account_name, to.id AS to,
       to.name AS to_name, r.proposed_by AS proposed_by, r.proposed_at AS proposed_at,
       r.decided_by AS decided_by, r.decided_at AS decided_at, r.note AS note,
       r.decision_note AS decision_note
ORDER BY proposed_at DESC
