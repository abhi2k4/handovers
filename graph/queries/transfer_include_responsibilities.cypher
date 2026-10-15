MATCH (t:Transfer {id: $id})-[:FROM]->(e:Employee)
MATCH (e)-[rf:RESPONSIBLE_FOR]->(r:Responsibility)
WHERE rf.until > $now
MERGE (t)-[i:INCLUDED]->(r)
SET i.reason = 'responsibility'
RETURN count(i) AS n
