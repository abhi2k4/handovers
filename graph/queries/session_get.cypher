// Who a session cookie belongs to, while it is valid and the person still works here
// (a leaver's session ends on their last day, whenever it was opened).
MATCH (s:Session {hash: $hash})-[:FOR]->(e)
WHERE s.expires_at > $now AND coalesce(e.status, 'active') <> 'departed'
RETURN e.id AS employee, e.name AS name, e.email AS email, s.id_token AS id_token
