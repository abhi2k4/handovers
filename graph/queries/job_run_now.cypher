// Bring a queued job forward to now (the "Run now" button, and the demo's pinned clock).
MATCH (j:Job {id: $id})
WHERE j.status IN ['queued', 'failed']
SET j.status = 'queued', j.run_at = $now
RETURN j.id AS id
