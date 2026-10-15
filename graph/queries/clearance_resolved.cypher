// Clearance rows the graph already resolves: someone else now holds admin of the account,
// or someone else now owns the work.
MATCH (h:Handover {id: $handover})-[:FOR]->(e:Employee)
MATCH (h)-[:CLEARS]->(c:ClearanceItem)
WHERE c.key STARTS WITH 'admin:' OR c.key STARTS WITH 'work:'
OPTIONAL MATCH (o:Employee)-[ha:HAS_ACCESS]->(:Account {id: c.target})
WHERE o <> e AND ha.role IN ['admin', 'owner'] AND ha.until > $now
OPTIONAL MATCH (w:Employee)-[rf:RESPONSIBLE_FOR]->(:Responsibility {id: c.target})
WHERE w <> e AND rf.until > $now
WITH c, collect(DISTINCT o.name) + collect(DISTINCT w.name) AS holders
WHERE size(holders) > 0
RETURN c.key AS key, holders
