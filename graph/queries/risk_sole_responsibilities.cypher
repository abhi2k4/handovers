// Responsibilities with exactly one current owner, per employee.
MATCH (e:Employee {status: 'active'})-[rf:RESPONSIBLE_FOR]->(r:Responsibility)
WHERE rf.until > $now
OPTIONAL MATCH (o:Employee {status: 'active'})-[rf2:RESPONSIBLE_FOR]->(r)
WHERE o.id <> e.id AND rf2.until > $now
WITH e, r, count(o) AS others
WHERE others = 0
WITH e, count(r) AS n
RETURN e.id AS employee, n
