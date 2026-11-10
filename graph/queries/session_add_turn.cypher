MERGE (se:Session {id: $session})
ON CREATE SET se.employee_id = $emp, se.started_at = $now
// Never add a turn to someone else's session.
WITH se
WHERE se.employee_id = $emp
CREATE (t:Turn {id: $turn, question: $question, answer: $answer, status: $status, at: $now})
CREATE (se)-[:HAS_TURN]->(t)
WITH t
UNWIND $used AS uid
MATCH (k:Knowledge {id: uid})
MERGE (t)-[:USED]->(k)
RETURN count(k) AS used
