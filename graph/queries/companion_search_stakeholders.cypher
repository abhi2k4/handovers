// External relationships this person now holds.
CALL db.idx.fulltext.queryNodes('Stakeholder', $q) YIELD node, score
MATCH (:Employee {id: $emp})-[w:WORKS_WITH]->(node)
WHERE w.until > $now
OPTIONAL MATCH (node)-[:EVIDENCED_BY]->(src:Source)
WITH node, score, w, collect(DISTINCT {id: src.id, kind: src.kind, title: src.title, at: src.occurred_at})[0..3] AS evidence
OPTIONAL MATCH (from:Employee {id: w.from_id})
RETURN node.id AS id, node.name AS name, node.org AS org, node.context AS context, score, w.via AS via,
       from.name AS from_name, evidence
ORDER BY score DESC
LIMIT $k
