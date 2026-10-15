// Baseline for the benchmark: full-text over every source, no graph scoping.
CALL db.idx.fulltext.queryNodes('Source', $q) YIELD node, score
RETURN node.id AS id, node.kind AS kind, node.title AS title, node.sensitivity AS sensitivity, score
ORDER BY score DESC
LIMIT $k
