// Abstention help: knowledge anywhere in the company that matches (content is never returned to the asker).
CALL db.idx.fulltext.queryNodes('Knowledge', $q) YIELD node, score
WHERE node.sensitivity <> 'personal' AND node.retracted_at > $now
RETURN node.id AS id, node.kind AS kind, node.title AS title, node.text AS text, node.value AS value, score
ORDER BY score DESC
LIMIT $k
