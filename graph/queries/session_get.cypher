// Who a session cookie belongs to, while it is valid.
MATCH (s:Session {hash: $hash})-[:FOR]->(e)
WHERE s.expires_at > $now
RETURN e.id AS employee, e.name AS name, e.email AS email, s.id_token AS id_token
