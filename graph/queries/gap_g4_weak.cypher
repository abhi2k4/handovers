// G4 weak support: unique knowledge backed by thin evidence.
MATCH (e:Employee {id: $emp})-[:KNOWS]->(k:Knowledge)
WHERE k.valid_to > $now AND k.retracted_at > $now AND k.sensitivity <> 'personal'
  AND k.confidence < $floor
OPTIONAL MATCH (o:Employee {status: 'active'})-[:KNOWS]->(k)
WHERE o.id <> $emp
WITH k, count(o) AS others
WHERE others = 0
RETURN k.id AS target, k.title AS title, k.kind AS kind, k.confidence AS confidence, k.sources AS sources
