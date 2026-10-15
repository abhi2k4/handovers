// Noisy-OR over distinct evidence: 1 - product(1 - quality), capped at 0.99.
MATCH (k:Knowledge)-[:EVIDENCED_BY]->(s:Source)
WITH k, collect(DISTINCT s) AS srcs
WITH k, srcs, 1 - reduce(p = 1.0, x IN srcs | p * (1 - x.quality)) AS c
SET k.confidence = CASE WHEN c > 0.99 THEN 0.99 ELSE c END, k.sources = size(srcs)
RETURN count(k) AS updated
