// "Sources disagree", settled by the leaver. Both claims stay in the graph: the one they named as
// current keeps going, the other is closed (valid_to) and marked superseded. The answer itself is
// a third node, the decision, linked to both: CONFIRMS the kept claim, RESOLVES the closed one.
MATCH (d:Knowledge {id: $decision}), (keep:Knowledge {id: $keep}), (old:Knowledge {id: $old})
MERGE (d)-[c:CONFIRMS]->(keep)
ON CREATE SET c.at = $now
MERGE (d)-[r:RESOLVES]->(old)
ON CREATE SET r.at = $now
MERGE (keep)-[s:SUPERSEDES]->(old)
ON CREATE SET s.at = $now, s.by = 'interview'
SET old.valid_to = CASE WHEN old.valid_to IS NULL OR old.valid_to > $now THEN $now ELSE old.valid_to END,
    old.status = 'superseded',
    keep.status = CASE WHEN keep.status = 'superseded' THEN 'current' ELSE keep.status END
RETURN keep.id AS kept, old.id AS closed
