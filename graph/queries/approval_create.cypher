MATCH (t:Transfer {id: $transfer}), (b:Employee {id: $by})
CREATE (a:Approval {id: $id, decision: $decision, at: $now, comment: $comment})
CREATE (t)-[:APPROVED_IN]->(a)
CREATE (a)-[:BY]->(b)
RETURN a.id AS id
