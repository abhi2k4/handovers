// The "why": a claim or procedure is justified by a decision.
MATCH (k:Knowledge {id: $id}), (d:Decision {id: $decision})
MERGE (k)-[:JUSTIFIED_BY]->(d)
RETURN d.id AS id
