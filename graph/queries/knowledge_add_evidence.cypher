// An interview answer confirms or documents existing knowledge.
MATCH (k:Knowledge {id: $id}), (s:Source {id: $source})
MERGE (k)-[ev:EVIDENCED_BY]->(s)
SET ev.quote = $quote
FOREACH (_ IN CASE WHEN $documented THEN [1] ELSE [] END | MERGE (k)-[:DOCUMENTED_IN]->(s))
RETURN k.id AS id
