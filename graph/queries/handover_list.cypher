MATCH (h:Handover)-[:FOR]->(e:Employee)
OPTIONAL MATCH (h)-[:HAS_GAP]->(g:Gap)
WITH h, e, count(g) AS gaps, sum(CASE WHEN g.status = 'open' THEN 1 ELSE 0 END) AS open_gaps
OPTIONAL MATCH (h)-[:SUCCESSOR]->(s:Employee)
RETURN h.id AS id, h.status AS status, h.created_at AS created_at, h.effective_at AS effective_at,
       e.id AS employee_id, e.name AS employee, e.title AS title, s.name AS successor, gaps, open_gaps
ORDER BY created_at DESC
