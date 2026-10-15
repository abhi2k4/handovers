MATCH (k:Knowledge {id: $id})
OPTIONAL MATCH (k)-[:ABOUT]->(a:Area)
WITH k, collect(a.id) AS areas
RETURN k.id AS id, k.kind AS kind, k.title AS title, k.value AS value, k.subject AS subject,
       k.predicate AS predicate, areas
