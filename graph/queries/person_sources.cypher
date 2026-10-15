MATCH (s:Source)-[:AUTHORED_BY]->(:Employee {id: $emp})
RETURN s.id AS id, s.kind AS kind, s.title AS title, s.occurred_at AS at, s.sensitivity AS sensitivity
ORDER BY at DESC
LIMIT $limit
