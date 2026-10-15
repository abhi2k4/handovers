MERGE (se:Session {id: $session})
ON CREATE SET se.employee_id = $emp, se.started_at = $now
CREATE (t:Turn {id: $turn, question: $question, answer: $answer, status: $status, at: $now})
CREATE (se)-[:HAS_TURN]->(t)
WITH t
UNWIND $used AS uid
MATCH (k:Knowledge {id: uid})
MERGE (t)-[:USED]->(k)
RETURN count(k) AS used
