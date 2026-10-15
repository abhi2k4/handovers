MATCH (h:Handover {id: $handover})-[:FOR]->(e:Employee), (h)-[:SUCCESSOR]->(s:Employee)
CREATE (t:Transfer {id: $id, status: 'planned', planned_at: $now})
CREATE (h)-[:HAS_TRANSFER]->(t)
CREATE (t)-[:FROM]->(e)
CREATE (t)-[:TO]->(s)
RETURN t.id AS id
