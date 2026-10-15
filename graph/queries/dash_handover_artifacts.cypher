MATCH (:Handover {id: $handover})-[:PRODUCED]->(a:Artifact)
RETURN a.kind AS kind
