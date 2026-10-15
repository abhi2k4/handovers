MATCH (t:Transfer {id: $id})-[r:INCLUDED|EXCLUDED]->(n)
RETURN type(r) AS decision, r.reason AS reason, n.id AS id, n.title AS title, n.name AS name,
       labels(n) AS labels
