MATCH (e:Employee)-[:MEMBER_OF]->(t:Team)
OPTIONAL MATCH (e)-[:REPORTS_TO]->(m:Employee)
OPTIONAL MATCH (h:Handover)-[:FOR]->(e)
WHERE h.status IN ['pending', 'analyzing', 'interview', 'review', 'approved', 'transferred']
RETURN e.id AS id, e.name AS name, e.title AS title, e.status AS status, t.id AS team_id,
       t.name AS team, m.name AS manager, h.id AS handover_id, h.status AS handover_status
ORDER BY team, name
