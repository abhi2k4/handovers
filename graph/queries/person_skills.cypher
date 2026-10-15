// Skill strength = number of their own sources that show the skill.
MATCH (:Employee {id: $emp})<-[:AUTHORED_BY]-(s:Source)-[:SHOWS_SKILL]->(k:Skill)
WITH k, count(DISTINCT s) AS evidence
RETURN k.id AS id, k.name AS name, k.category AS category, evidence
ORDER BY evidence DESC
