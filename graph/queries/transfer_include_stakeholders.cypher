MATCH (t:Transfer {id: $id})-[:FROM]->(e:Employee)
MATCH (e)-[w:WORKS_WITH]->(st:Stakeholder)
WHERE w.until > $now
MERGE (t)-[i:INCLUDED]->(st)
SET i.reason = 'relationship'
RETURN count(i) AS n
