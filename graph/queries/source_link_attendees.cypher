MATCH (s:Source {id: $id})
UNWIND $attendees AS pid
MATCH (e:Employee {id: pid})
MERGE (s)-[:ATTENDED_BY]->(e)
RETURN count(e) AS linked
