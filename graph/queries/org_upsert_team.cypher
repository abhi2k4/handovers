// Team in the org chart.
MERGE (t:Team {id: $id})
SET t.name = $name
RETURN t.id AS id
