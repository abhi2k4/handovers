// What decides whether someone can take over a leaver's work: still here, not leaving, which team.
MATCH (e:Employee {id: $id})
OPTIONAL MATCH (e)-[:MEMBER_OF]->(t:Team)
OPTIONAL MATCH (h:Handover)-[:FOR]->(e)
WHERE h.status <> 'cancelled'
WITH e, t, count(h) AS handovers
RETURN e.id AS id, e.name AS name, e.status AS status, t.id AS team_id, t.name AS team,
       handovers > 0 AS leaving
