// Create the clearance rows of a handover once; existing rows keep their status.
MATCH (h:Handover {id: $handover})
UNWIND $items AS it
MERGE (c:ClearanceItem {id: it.id})
ON CREATE SET c.key = it.key, c.label = it.label, c.group = it.group, c.owner = it.owner,
              c.target = it.target, c.ord = it.ord, c.status = 'open', c.updated_at = $now
MERGE (h)-[:CLEARS]->(c)
RETURN count(c) AS items
