MATCH (t:Transfer {id: $id})-[:TO]->(s:Employee), (t)-[:FROM]->(e:Employee),
      (t)-[:APPROVED_IN]->(:Approval {decision: 'approved'})
MATCH (t)-[:INCLUDED]->(r:Responsibility)
MATCH (e)-[old:RESPONSIBLE_FOR]->(r)
SET old.until = $now
MERGE (s)-[rf:RESPONSIBLE_FOR]->(r)
ON CREATE SET rf.since = $now, rf.until = $open, rf.via = 'transfer', rf.transfer_id = t.id,
              rf.from_id = e.id, rf.last_seen = $now
RETURN count(rf) AS applied
