// The last few turns of a companion conversation, newest first (for follow-up questions).
// Only the person's own session: a session id sent by someone else matches nothing.
MATCH (:Session {id: $session, employee_id: $emp})-[:HAS_TURN]->(t:Turn)
RETURN t.question AS question, t.answer AS answer, t.status AS status, t.at AS at
ORDER BY at DESC
LIMIT $limit
