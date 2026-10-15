CREATE (a:AuditEvent {id: $id, type: $type, at: $now, payload: $payload, actor: $actor})
WITH a
OPTIONAL MATCH (h:Handover {id: $handover})
FOREACH (_ IN CASE WHEN h IS NULL THEN [] ELSE [1] END | MERGE (a)-[:RECORDED]->(h))
RETURN a.id AS id
