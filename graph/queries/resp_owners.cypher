// Current owners of a responsibility (for access checks before assigning a backup).
MATCH (e:Employee)-[rf:RESPONSIBLE_FOR]->(r:Responsibility {id: $id})
WHERE rf.until > $now
RETURN e.id AS id, e.name AS name
