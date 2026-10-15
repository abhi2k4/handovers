MATCH (:Handover {id: $handover})-[:HAS_NOTE]->(n:Note)
RETURN n.id AS id, n.kind AS kind, n.text AS text, n.by AS by, n.by_name AS by_name, n.at AS at
ORDER BY at DESC
