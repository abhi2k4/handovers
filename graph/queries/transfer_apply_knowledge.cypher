// Successor gains KNOWS edges to the SAME knowledge nodes, with lineage. Nothing is copied.
MATCH (t:Transfer {id: $id})-[:TO]->(s:Employee), (t)-[:FROM]->(e:Employee),
      (t)-[:APPROVED_IN]->(ap:Approval {decision: 'approved'})
MATCH (t)-[:INCLUDED]->(k:Knowledge)
MERGE (s)-[kn:KNOWS]->(k)
ON CREATE SET kn.via = 'transfer', kn.since = $now, kn.private = false, kn.transfer_id = t.id,
              kn.from_id = e.id, kn.approval_id = ap.id
RETURN count(kn) AS applied
