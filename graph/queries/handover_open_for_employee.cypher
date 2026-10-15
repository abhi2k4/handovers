// A live handover for this person: in progress, or transferred while they are still here.
MATCH (h:Handover)-[:FOR]->(e:Employee {id: $emp})
WHERE h.status IN ['pending', 'analyzing', 'interview', 'review', 'approved']
   OR (h.status = 'transferred' AND e.status <> 'departed')
RETURN h.id AS id
