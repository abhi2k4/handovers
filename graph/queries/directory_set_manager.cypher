// The directory is the source of truth for who reports to whom: one current manager per person.
MATCH (e:Employee {email: $email}), (m:Employee {email: $manager})
WHERE e <> m
OPTIONAL MATCH (e)-[old:REPORTS_TO]->(x:Employee)
WHERE x <> m
DELETE old
MERGE (e)-[:REPORTS_TO]->(m)
RETURN m.id AS manager
