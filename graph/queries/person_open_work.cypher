MATCH (s:Ticket)-[:AUTHORED_BY]->(:Employee {id: $emp})
WHERE s.status = 'open'
RETURN s.id AS id, s.title AS title, s.occurred_at AS opened, s.url AS url
ORDER BY opened
