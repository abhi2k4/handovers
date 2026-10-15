// Benchmark: which sources evidence these items (to score the flat-search baseline fairly).
MATCH (n)-[:EVIDENCED_BY]->(s:Source)
WHERE n.id IN $ids
WITH n, collect(DISTINCT s.id) AS sources
RETURN n.id AS id, sources
