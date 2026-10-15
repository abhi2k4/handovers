// Accounts where one person is the only admin or owner.
MATCH (e:Employee {status: 'active'})-[h:HAS_ACCESS]->(a:Account)
WHERE h.until > $now AND h.role IN ['admin', 'owner']
OPTIONAL MATCH (o:Employee)-[h2:HAS_ACCESS]->(a)
WHERE o.status IN ['active', 'incoming'] AND o.id <> e.id AND h2.until > $now AND h2.role IN ['admin', 'owner']
WITH e, a, count(o) AS others
WHERE others = 0
WITH e, count(a) AS n
RETURN e.id AS employee, n
