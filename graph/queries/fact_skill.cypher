MATCH (s:Source {id: $source})
MERGE (k:Skill {id: $key})
ON CREATE SET k.name = $title, k.category = coalesce($category, 'skill'), k.aliases = []
MERGE (s)-[:SHOWS_SKILL]->(k)
RETURN k.id AS id
