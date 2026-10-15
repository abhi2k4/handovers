// A proposed account handover (by the manager or IT), waiting for HR. Nothing changes in access
// until HR approves. One open proposal per account and handover: a new one replaces the old.
MATCH (h:Handover {id: $handover}), (a:Account {id: $account}), (to:Employee {id: $to})
OPTIONAL MATCH (h)-[:HAS_REASSIGNMENT]->(old:Reassignment {status: 'proposed'})-[:OF]->(a)
SET old.status = 'replaced', old.decided_at = $now
CREATE (r:Reassignment {id: $id, status: 'proposed', proposed_by: $by, proposed_at: $now, note: $note})
CREATE (h)-[:HAS_REASSIGNMENT]->(r)
CREATE (r)-[:OF]->(a)
CREATE (r)-[:TO]->(to)
RETURN r.id AS id
