MATCH (e:Employee {id: $emp})-[:MEMBER_OF]->(t:Team)
OPTIONAL MATCH (e)<-[:AUTHORED_BY]-(s:Source)
WITH e, t, count(DISTINCT s) AS sources
OPTIONAL MATCH (e)-[:HAS_ROLE]->(r:Role)
OPTIONAL MATCH (e)-[:REPORTS_TO]->(m:Employee)
RETURN e.id AS id, e.name AS name, e.title AS title, e.email AS email, e.status AS status,
       e.joined_at AS joined_at, t.id AS team_id, t.name AS team, r.id AS role_id, r.title AS role,
       m.id AS manager_id, m.name AS manager, sources
