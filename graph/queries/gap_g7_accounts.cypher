// G7 sole access: the leaver is the only admin or owner.
MATCH (e:Employee {id: $emp})-[h:HAS_ACCESS]->(a:Account)
WHERE h.until > $now AND h.role IN ['admin', 'owner']
OPTIONAL MATCH (o:Employee)-[h2:HAS_ACCESS]->(a)
WHERE o.status IN ['active', 'incoming'] AND o.id <> $emp AND h2.until > $now AND h2.role IN ['admin', 'owner']
WITH a, h, count(o) AS others
WHERE others = 0
RETURN a.id AS target, a.name AS title, a.system AS system, h.role AS role
