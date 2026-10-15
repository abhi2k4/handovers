// G7 sole owner: nobody else currently does this.
MATCH (e:Employee {id: $emp})-[rf:RESPONSIBLE_FOR]->(r:Responsibility)
WHERE rf.until > $now
OPTIONAL MATCH (o:Employee {status: 'active'})-[rf2:RESPONSIBLE_FOR]->(r)
WHERE o.id <> $emp AND rf2.until > $now
WITH r, count(o) AS others
WHERE others = 0
RETURN r.id AS target, r.title AS title, r.cadence AS cadence
