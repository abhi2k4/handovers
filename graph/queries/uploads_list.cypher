MATCH (s:Source)
WHERE s.origin = 'upload'
OPTIONAL MATCH (n)-[:EVIDENCED_BY]->(s)
WITH s, count(DISTINCT n) AS facts
OPTIONAL MATCH (s)-[:AUTHORED_BY]->(e:Employee)
RETURN s.id AS id, s.title AS title, s.kind AS kind, s.ingested_at AS at, e.name AS employee, facts
ORDER BY at DESC
