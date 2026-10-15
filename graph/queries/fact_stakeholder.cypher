// An external party someone works with. touches counts the evidence.
MATCH (s:Source {id: $source})
MERGE (st:Stakeholder {id: $key})
ON CREATE SET st.name = $title, st.org = $org, st.kind = $stakeholder_kind, st.origin = $origin
SET st.context = coalesce($context, st.context)
MERGE (st)-[ev:EVIDENCED_BY]->(s)
SET ev.quote = $quote
FOREACH (aid IN $areas | MERGE (ar:Area {id: aid}) MERGE (st)-[:ABOUT]->(ar))
WITH st
UNWIND $people AS pid
MATCH (e:Employee {id: pid})
MERGE (e)-[w:WORKS_WITH]->(st)
ON CREATE SET w.since = $occurred_at, w.until = $open, w.touches = 0, w.via = 'observed'
SET w.touches = w.touches + 1, w.context = coalesce($context, w.context),
    w.last_seen = CASE WHEN w.last_seen IS NULL OR w.last_seen < $occurred_at THEN $occurred_at ELSE w.last_seen END
RETURN count(w) AS linked
