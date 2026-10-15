// External relationships held by exactly one person.
MATCH (e:Employee {status: 'active'})-[w:WORKS_WITH]->(st:Stakeholder)
WHERE w.until > $now
OPTIONAL MATCH (o:Employee {status: 'active'})-[w2:WORKS_WITH]->(st)
WHERE o.id <> e.id AND w2.until > $now
WITH e, st, count(o) AS others
WHERE others = 0
WITH e, count(st) AS n
RETURN e.id AS employee, n
