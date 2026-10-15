// Assign a backup: a second current owner, so the work no longer rests on one person.
MATCH (r:Responsibility {id: $id})
MATCH (b:Employee {id: $emp, status: 'active'})
MERGE (b)-[rf:RESPONSIBLE_FOR]->(r)
ON CREATE SET rf.since = $now, rf.until = $open, rf.via = 'backup', rf.assigned_by = $by
ON MATCH SET rf.until = CASE WHEN rf.until > $now THEN rf.until ELSE $open END
RETURN r.id AS id, r.title AS title, b.name AS backup
