// Everything someone knows, with who else holds it and whether it is written down.
MATCH (e:Employee {id: $emp})-[kn:KNOWS]->(k:Knowledge)
WHERE k.retracted_at > $now AND kn.revoked_at IS NULL
OPTIONAL MATCH (o:Employee {status: 'active'})-[kn2:KNOWS]->(k)
WHERE o.id <> $emp AND kn2.revoked_at IS NULL
WITH kn, k, collect(DISTINCT o.name) AS others
OPTIONAL MATCH (k)-[:DOCUMENTED_IN]->(d:Source)
WITH kn, k, others, count(DISTINCT d) AS docs
OPTIONAL MATCH (k)-[:JUSTIFIED_BY]->(j:Decision)
WITH kn, k, others, docs, collect(j.title) AS reasons
RETURN k.id AS id, k.kind AS kind, k.title AS title, k.rationale AS rationale, k.value AS value,
       k.steps AS steps, k.status AS status, k.valid_from AS valid_from, k.valid_to AS valid_to,
       k.confidence AS confidence, k.sources AS sources, k.sensitivity AS sensitivity,
       kn.private AS private, kn.via AS via, others, docs > 0 AS documented,
       reasons[0] AS justified_by
ORDER BY kind, valid_from DESC
