MATCH (h:Handover)-[:HAS_GAP]->(g:Gap {id: $id})
MATCH (h)-[:FOR]->(e:Employee)
RETURN g.id AS id, g.rule AS rule, g.target_id AS target_id, g.target_kind AS target_kind,
       g.title AS title, g.question AS question, g.status AS status, g.context AS context,
       h.id AS handover_id,
       e.id AS employee_id
