// Who is calling: the employee, their team, direct reports, and the handovers they are part of.
// Grouped by nodes, properties projected last (FalkorDB 6.0.1 crashes on null grouping keys).
MATCH (e:Employee {id: $emp})
OPTIONAL MATCH (e)-[:MEMBER_OF]->(t:Team)
OPTIONAL MATCH (r:Employee)-[:REPORTS_TO]->(e)
WITH e, t, collect(DISTINCT r.id) AS reports
OPTIONAL MATCH (hl:Handover)-[:FOR]->(e)
WITH e, t, reports, collect(DISTINCT {id: hl.id, status: hl.status}) AS leaving
OPTIONAL MATCH (hs:Handover)-[:SUCCESSOR]->(e)
WITH e, t, reports, leaving, collect(DISTINCT {id: hs.id, status: hs.status}) AS succeeding
OPTIONAL MATCH (hm:Handover)-[:FOR]->(:Employee)-[:REPORTS_TO]->(e)
WITH e, t, reports, leaving, succeeding, collect(DISTINCT {id: hm.id, status: hm.status}) AS managing
RETURN e.id AS id, e.name AS name, e.title AS title, e.status AS status, e.groups AS groups, t.id AS team_id,
       t.name AS team, reports, leaving, succeeding, managing
