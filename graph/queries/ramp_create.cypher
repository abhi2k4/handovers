// Store a generated ramp-up plan: RampPlan -FROM-> Handover, -FOR-> successor,
// -HAS_ITEM-> RampItem -ABOUT-> the graph node the item comes from.
MATCH (h:Handover {id: $handover})-[:SUCCESSOR]->(s:Employee)
CREATE (p:RampPlan {id: $id, status: 'draft', created_at: $now, method: $method})
CREATE (p)-[:FROM]->(h)
CREATE (p)-[:FOR]->(s)
WITH p
UNWIND $items AS it
CREATE (i:RampItem {id: it.id, week: it.week, kind: it.kind, title: it.title, why: it.why,
                    about: it.about, ord: it.ord, removed: false})
CREATE (p)-[:HAS_ITEM]->(i)
WITH i, it
OPTIONAL MATCH (x {id: it.about})
FOREACH (_ IN CASE WHEN x IS NULL THEN [] ELSE [1] END | CREATE (i)-[:ABOUT]->(x))
RETURN count(i) AS items
