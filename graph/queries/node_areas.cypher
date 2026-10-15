// Areas of any responsibility, account or stakeholder (used to place interview answers).
MATCH (n)-[:ABOUT]->(a:Area)
WHERE n.id = $id
RETURN collect(DISTINCT a.id) AS areas
