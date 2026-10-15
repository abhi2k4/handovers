// Successor ramp-up plan for a handover, with its items (docs/product-strategy.md section 11).
// Grouped by node, properties projected after (FalkorDB 6.0.1 crashes on null grouping keys).
MATCH (p:RampPlan)-[:FROM]->(h:Handover {id: $handover})
OPTIONAL MATCH (p)-[:HAS_ITEM]->(i:RampItem)
WITH p, collect({id: i.id, week: i.week, kind: i.kind, title: i.title, why: i.why, about: i.about,
                 ord: i.ord, removed: i.removed, done_at: i.done_at}) AS items
RETURN p.id AS id, p.status AS status, p.created_at AS created_at, p.method AS method,
       p.approved_at AS approved_at, p.approved_by AS approved_by, items
