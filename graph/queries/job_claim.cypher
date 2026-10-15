// Take the jobs that are due. FalkorDB runs one write query at a time, so a job is claimed once.
MATCH (j:Job {status: 'queued'})
WHERE j.run_at <= $now
WITH j ORDER BY j.run_at LIMIT $limit
SET j.status = 'running', j.started_at = $now, j.attempts = j.attempts + 1
RETURN j.id AS id, j.key AS key, j.kind AS kind, j.payload AS payload, j.handover AS handover,
       j.attempts AS attempts, j.run_at AS run_at
