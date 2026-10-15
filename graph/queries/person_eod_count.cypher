MATCH (s:EOD)-[:AUTHORED_BY]->(:Employee {id: $emp})
RETURN count(s) AS n
