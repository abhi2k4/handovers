MATCH (h:Handover {id: $id}), (s:Employee {id: $successor})
OPTIONAL MATCH (h)-[old:SUCCESSOR]->()
DELETE old
MERGE (h)-[:SUCCESSOR]->(s)
RETURN s.id AS id
