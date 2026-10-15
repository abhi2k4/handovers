// Who may approve each live handover: the leaver's management chain, nearest first, with whether
// each manager is still here and not leaving themselves. services/access.pick_approver walks it
// (direct manager, then skip-level, then HR). Depth is capped at 4 levels.
MATCH (h:Handover)-[:FOR]->(e:Employee)
WHERE h.status <> 'cancelled'
OPTIONAL MATCH path = (e)-[:REPORTS_TO*1..4]->(m:Employee)
OPTIONAL MATCH (hm:Handover)-[:FOR]->(m)
WHERE hm.status <> 'cancelled'
WITH h, e, m, path, count(hm) AS leaving_count
WITH h, e, collect(CASE WHEN m IS NULL THEN NULL ELSE
       {id: m.id, name: m.name, status: m.status, depth: length(path), leaving: leaving_count > 0}
     END) AS chain
RETURN h.id AS handover, e.id AS leaver, chain
