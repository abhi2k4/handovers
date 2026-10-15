// Per team: current responsibilities, and how many of them only one active person does.
MATCH (t:Team)<-[:MEMBER_OF]-(e:Employee {status: 'active'})-[rf:RESPONSIBLE_FOR]->(r:Responsibility)
WHERE rf.until > $now
WITH DISTINCT t, r
OPTIONAL MATCH (o:Employee {status: 'active'})-[rf2:RESPONSIBLE_FOR]->(r)
WHERE rf2.until > $now
WITH t, r, count(DISTINCT o) AS owners
WITH t, count(r) AS total, sum(CASE WHEN owners = 1 THEN 1 ELSE 0 END) AS sole
RETURN t.id AS id, t.name AS name, total, sole
ORDER BY name
