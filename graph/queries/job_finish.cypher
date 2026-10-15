// A job ran: done, failed for good, or back in the queue for a retry at $retry_at.
MATCH (j:Job {id: $id})
SET j.status = $status, j.finished_at = $now, j.result = $result, j.last_error = $error,
    j.run_at = CASE WHEN $status = 'queued' THEN $retry_at ELSE j.run_at END
RETURN j.id AS id, j.status AS status
