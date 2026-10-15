// The most recent uploaded job description for this person's role.
MATCH (:Employee {id: $emp})-[:HAS_ROLE]->(r:Role)<-[:DESCRIBES]-(d:Document)
RETURN d.id AS id, d.title AS title, d.text AS text, d.occurred_at AS at, r.title AS role
ORDER BY at DESC
LIMIT 1
