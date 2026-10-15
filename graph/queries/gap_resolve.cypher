MATCH (g:Gap {id: $id}), (a:Source {id: $answer})
MERGE (g)-[:RESOLVED_BY]->(a)
SET g.status = 'answered', g.answered_at = $now
RETURN g.id AS id
