// G8 recurring fix, no procedure: the leaver keeps fixing the same thing and the steps exist nowhere.
MATCH (e:Employee {id: $emp})-[rf:RESPONSIBLE_FOR]->(r:Responsibility)
WHERE rf.until > $now
MATCH (r)-[:EVIDENCED_BY]->(t:Ticket)
WITH r, count(DISTINCT t) AS fixes
WHERE fixes >= $min_repeats
OPTIONAL MATCH (p:Procedure)
WHERE p.handles = r.id AND p.valid_to > $now
WITH r, fixes, count(p) AS procedures
WHERE procedures = 0
RETURN r.id AS target, r.title AS title, fixes
