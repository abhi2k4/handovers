// G2 undocumented: a decision or procedure only the leaver holds that is written down nowhere.
MATCH (e:Employee {id: $emp})-[:KNOWS]->(k:Knowledge)
WHERE (k:Decision OR k:Procedure) AND k.valid_to > $now AND k.retracted_at > $now
  AND k.sensitivity <> 'personal' AND NOT (k)-[:DOCUMENTED_IN]->(:Source)
OPTIONAL MATCH (o:Employee {status: 'active'})-[:KNOWS]->(k)
WHERE o.id <> $emp
WITH k, count(o) AS others
WHERE others = 0
RETURN k.id AS target, k.title AS title, k.kind AS kind, k.confidence AS confidence
