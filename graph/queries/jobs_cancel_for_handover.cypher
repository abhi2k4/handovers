MATCH (j:Job {handover: $handover, status: 'queued'})
SET j.status = 'cancelled', j.finished_at = $now
RETURN count(j) AS cancelled
