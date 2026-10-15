// A generated HR output (JD, screening kit, interview kit, handover plan), stored as JSON.
MATCH (h:Handover {id: $handover})
MERGE (a:Artifact {id: $id})
SET a.kind = $kind, a.content = $content, a.updated_at = $now, a.model = $model
MERGE (h)-[:PRODUCED]->(a)
RETURN a.id AS id
