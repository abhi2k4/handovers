// A cancelled handover: proposals still waiting for HR are withdrawn.
MATCH (:Handover {id: $handover})-[:HAS_REASSIGNMENT]->(r:Reassignment {status: 'proposed'})
SET r.status = 'withdrawn', r.decided_at = $now
RETURN count(r) AS withdrawn
