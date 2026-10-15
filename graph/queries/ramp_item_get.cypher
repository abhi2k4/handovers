// A ramp-up item with its plan state and handover, for access checks.
MATCH (p:RampPlan)-[:HAS_ITEM]->(i:RampItem {id: $id})
MATCH (p)-[:FROM]->(h:Handover)
RETURN i.id AS id, p.status AS status, h.id AS handover
