// Benchmark baseline: copy every memory of the leaver to the successor, no review, no filters.
MATCH (e:Employee {id: $from})-[:KNOWS]->(k:Knowledge), (s:Employee {id: $to})
MERGE (s)-[kn:KNOWS]->(k)
ON CREATE SET kn.via = 'naive', kn.private = false
RETURN count(kn) AS copied
