MATCH (e:Employee {id: $id}), (m:Employee {id: $manager})
MERGE (e)-[:REPORTS_TO]->(m)
RETURN m.id AS manager
