// G1 missing rationale: a decision only the leaver holds, recorded without a reason.
MATCH (e:Employee {id: $emp})-[:KNOWS]->(d:Decision)
WHERE d.valid_to > $now AND d.retracted_at > $now AND d.sensitivity <> 'personal'
  AND (d.rationale IS NULL OR d.rationale = '')
OPTIONAL MATCH (o:Employee {status: 'active'})-[:KNOWS]->(d)
WHERE o.id <> $emp
WITH d, count(o) AS others
WHERE others = 0
RETURN d.id AS target, d.title AS title, d.confidence AS confidence
