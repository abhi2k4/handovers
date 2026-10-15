// Suggested receivers: active colleagues ranked by evidence of the needed skills.
MATCH (o:Employee {status: 'active'})<-[:AUTHORED_BY]-(s:Source)-[:SHOWS_SKILL]->(k:Skill)
WHERE o.id <> $emp AND k.id IN $skills
WITH o, count(DISTINCT s) AS strength
RETURN o.id AS id, o.name AS name, strength
ORDER BY strength DESC
LIMIT 3
