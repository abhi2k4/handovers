MATCH (t:Transfer {id: $id})
UNWIND $items AS it
MATCH (k:Knowledge {id: it.id})
MERGE (t)-[i:INCLUDED]->(k)
SET i.reason = it.reason
RETURN count(i) AS n
