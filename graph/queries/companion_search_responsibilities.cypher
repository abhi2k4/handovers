// Responsibilities this person now holds (inherited ones carry who they came from).
CALL db.idx.fulltext.queryNodes('Responsibility', $q) YIELD node, score
MATCH (:Employee {id: $emp})-[rf:RESPONSIBLE_FOR]->(node)
WHERE rf.until > $now
OPTIONAL MATCH (node)-[:EVIDENCED_BY]->(src:Source)
WITH node, score, rf, collect(DISTINCT {id: src.id, kind: src.kind, title: src.title, at: src.occurred_at})[0..3] AS evidence
OPTIONAL MATCH (from:Employee {id: rf.from_id})
RETURN node.id AS id, node.title AS title, node.cadence AS cadence, score, rf.via AS via, from.name AS from_name,
       evidence
ORDER BY score DESC
LIMIT $k
