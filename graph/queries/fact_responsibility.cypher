// A duty someone performs. Evidence links to the source; RESPONSIBLE_FOR is time-bounded.
MATCH (s:Source {id: $source})
MERGE (r:Responsibility {id: $key})
ON CREATE SET r.title = $title, r.created_at = $occurred_at, r.origin = $origin
SET r.cadence = coalesce($cadence, r.cadence)
MERGE (r)-[ev:EVIDENCED_BY]->(s)
SET ev.quote = $quote
FOREACH (aid IN $areas | MERGE (a:Area {id: aid}) MERGE (r)-[:ABOUT]->(a))
FOREACH (sid IN $skills | MERGE (k:Skill {id: sid}) MERGE (r)-[:NEEDS_SKILL]->(k))
WITH r
UNWIND $people AS pid
MATCH (e:Employee {id: pid})
MERGE (e)-[rf:RESPONSIBLE_FOR]->(r)
ON CREATE SET rf.since = $occurred_at, rf.until = $open, rf.via = 'observed'
SET rf.last_seen = CASE WHEN rf.last_seen IS NULL OR rf.last_seen < $occurred_at THEN $occurred_at ELSE rf.last_seen END
RETURN count(rf) AS linked
