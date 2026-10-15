// The approver sends the transfer back: a Transfer that never applies, with the rejection and
// its reason. Nothing moves to the successor; the next approval creates a new Transfer.
MATCH (h:Handover {id: $handover})-[:FOR]->(e:Employee), (b:Employee {id: $by})
OPTIONAL MATCH (h)-[:SUCCESSOR]->(s:Employee)
CREATE (t:Transfer {id: $id, status: 'rejected', planned_at: $now})
CREATE (h)-[:HAS_TRANSFER]->(t)
CREATE (t)-[:FROM]->(e)
CREATE (a:Approval {id: $approval, decision: 'rejected', at: $now, comment: $comment})
CREATE (t)-[:APPROVED_IN]->(a)
CREATE (a)-[:BY]->(b)
RETURN t.id AS id
