// A signed-in session. Only the hash of the cookie's token is stored, never the token itself.
MATCH (e {id: $employee}) WHERE e:Employee OR e:Operator
CREATE (s:Session {hash: $hash, created_at: $now, expires_at: $expires, id_token: $id_token})
CREATE (s)-[:FOR]->(e)
RETURN e.id AS employee
