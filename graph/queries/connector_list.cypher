// State of every connector account that has been set up, synced or tested: sync counts, whether
// it is the active one in its category, the last test of its saved settings, and the teams it serves.
MATCH (c:Connector)
OPTIONAL MATCH (c)-[:SERVES]->(t:Team)
WITH c, [x IN collect({id: t.id, name: t.name}) WHERE x.id IS NOT NULL] AS teams
RETURN c.id AS id, coalesce(c.platform, c.id) AS platform, c.label AS label, teams,
       c.status AS status, c.last_sync AS last_sync, c.cursor AS cursor,
       c.sources AS sources, c.facts AS facts, c.review AS review, c.people AS people,
       c.error AS error, coalesce(c.active, false) AS active,
       c.test_ok AS test_ok, c.test_message AS test_message, c.tested_at AS tested_at
