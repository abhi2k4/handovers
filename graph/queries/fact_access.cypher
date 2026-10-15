// An account or asset someone controls (admin rights, billing, ownership).
MATCH (s:Source {id: $source})
MERGE (a:Account {id: $key})
ON CREATE SET a.name = $title, a.system = $system, a.origin = $origin
MERGE (a)-[ev:EVIDENCED_BY]->(s)
SET ev.quote = $quote
FOREACH (aid IN $areas | MERGE (ar:Area {id: aid}) MERGE (a)-[:ABOUT]->(ar))
WITH a
UNWIND $people AS pid
MATCH (e:Employee {id: pid})
MERGE (e)-[h:HAS_ACCESS]->(a)
ON CREATE SET h.since = $occurred_at, h.until = $open, h.via = 'observed'
SET h.role = coalesce($role, h.role, 'member')
RETURN count(h) AS linked
