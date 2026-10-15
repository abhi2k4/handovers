// Who else holds these items (names only).
MATCH (o:Employee {status: 'active'})-[kn:KNOWS]->(k:Knowledge)
WHERE k.id IN $ids AND o.id <> $emp AND kn.private = false AND k.sensitivity <> 'personal'
WITH o, count(k) AS hits
RETURN o.id AS id, o.name AS name, o.title AS title, hits
ORDER BY hits DESC
LIMIT 3
