// Active people in one team (HR runs exits; in the sample company HR also owns IT).
MATCH (e:Employee {status: 'active'})-[:MEMBER_OF]->(:Team {id: $team})
RETURN e.id AS id, e.name AS name, e.title AS title
