// Employee with team and role membership.
MATCH (t:Team {id: $team}), (r:Role {id: $role})
MERGE (e:Employee {id: $id})
SET e.name = $name, e.email = $email, e.title = $title, e.status = $status, e.joined_at = $joined_at
MERGE (e)-[:MEMBER_OF]->(t)
MERGE (e)-[hr:HAS_ROLE]->(r)
ON CREATE SET hr.valid_from = $joined_at, hr.valid_to = $open
RETURN e.id AS id
