// The last few turns of a companion conversation, newest first (for follow-up questions).
MATCH (:Session {id: $session})-[:HAS_TURN]->(t:Turn)
RETURN t.question AS question, t.answer AS answer, t.status AS status, t.at AS at
ORDER BY at DESC
LIMIT $limit
