// Successor's agent: full-text candidates, restricted to knowledge this person holds.
CALL db.idx.fulltext.queryNodes('Knowledge', $q) YIELD node, score
MATCH (:Employee {id: $emp})-[kn:KNOWS]->(node)
WHERE node.retracted_at > $now AND kn.revoked_at IS NULL
RETURN node.id AS id, node.kind AS kind, node.title AS title, node.text AS text, node.value AS value, node.valid_to AS valid_to, score,
       kn.via AS via
ORDER BY score DESC
LIMIT $k
