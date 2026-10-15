// An uploaded job description describes a role.
MATCH (s:Source {id: $id}), (r:Role {id: $role})
MERGE (s)-[:DESCRIBES]->(r)
RETURN r.id AS role
