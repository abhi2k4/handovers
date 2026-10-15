MATCH (e:Employee {id: $emp})-[h:HAS_ACCESS]->(a:Account)
WHERE h.until > $now
OPTIONAL MATCH (o:Employee)-[h2:HAS_ACCESS]->(a)
WHERE o.status IN ['active', 'incoming'] AND o.id <> $emp AND h2.until > $now AND coalesce(h2.since, 0) <= $now AND h2.role IN ['admin', 'owner']
WITH a, h, collect(DISTINCT o.name) AS other_admins
RETURN a.id AS id, a.name AS name, a.system AS system, h.role AS role, h.since AS since, other_admins
ORDER BY name
