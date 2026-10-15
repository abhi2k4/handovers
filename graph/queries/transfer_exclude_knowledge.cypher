MATCH (t:Transfer {id: $id})
UNWIND $items AS it
MATCH (k:Knowledge {id: it.id})
MERGE (t)-[x:EXCLUDED]->(k)
SET x.reason = it.reason
RETURN count(x) AS n
