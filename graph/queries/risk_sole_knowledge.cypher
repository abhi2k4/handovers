// Current knowledge no other active employee holds.
MATCH (e:Employee {status: 'active'})-[:KNOWS]->(k:Knowledge)
WHERE k.valid_to > $now AND k.retracted_at > $now AND k.sensitivity <> 'personal'
OPTIONAL MATCH (o:Employee {status: 'active'})-[:KNOWS]->(k)
WHERE o.id <> e.id
WITH e, k, count(o) AS others
WHERE others = 0
WITH e, count(k) AS n
RETURN e.id AS employee, n
