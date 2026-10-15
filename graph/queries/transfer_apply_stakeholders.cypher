MATCH (t:Transfer {id: $id})-[:TO]->(s:Employee), (t)-[:FROM]->(e:Employee),
      (t)-[:APPROVED_IN]->(:Approval {decision: 'approved'})
MATCH (t)-[:INCLUDED]->(st:Stakeholder)
MATCH (e)-[old:WORKS_WITH]->(st)
SET old.until = $now
MERGE (s)-[w:WORKS_WITH]->(st)
ON CREATE SET w.since = $now, w.until = $open, w.via = 'transfer', w.transfer_id = t.id,
              w.from_id = e.id, w.touches = 0, w.context = old.context
RETURN count(w) AS applied
