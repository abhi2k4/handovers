// G1 missing rationale: a current claim only the leaver holds, with no decision behind it.
MATCH (e:Employee {id: $emp})-[:KNOWS]->(c:Claim)
WHERE c.valid_to > $now AND c.retracted_at > $now AND c.sensitivity <> 'personal'
  AND c.predicate IN $predicates AND NOT (c)-[:JUSTIFIED_BY]->(:Decision)
OPTIONAL MATCH (o:Employee {status: 'active'})-[:KNOWS]->(c)
WHERE o.id <> $emp
WITH c, count(o) AS others
WHERE others = 0
OPTIONAL MATCH (c)-[:SUPERSEDES]->(prev:Claim)
RETURN c.id AS target, c.title AS title, c.subject AS subject, c.predicate AS predicate,
       c.value AS value, prev.value AS previous, c.confidence AS confidence
