// Every team, for assigning work-tool accounts to the teams they serve.
MATCH (t:Team)
RETURN t.id AS id, t.name AS name
ORDER BY t.name
