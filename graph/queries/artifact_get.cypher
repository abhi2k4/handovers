MATCH (:Handover {id: $handover})-[:PRODUCED]->(a:Artifact {kind: $kind})
RETURN a.id AS id, a.content AS content, a.updated_at AS updated_at, a.model AS model
