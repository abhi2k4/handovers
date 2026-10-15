MATCH (a:AuditEvent)-[:RECORDED]->(:Handover {id: $handover})
RETURN a.type AS type, a.at AS at, a.payload AS payload, a.actor AS actor
ORDER BY at
