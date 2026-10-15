// Queue a background job (services/jobs.py). `key` makes it idempotent: queuing the same key
// again while it waits only moves its time.
MERGE (j:Job {key: $key})
ON CREATE SET j.id = $id, j.kind = $kind, j.status = 'queued', j.run_at = $run_at, j.attempts = 0,
              j.payload = $payload, j.handover = $handover, j.created_at = $now
ON MATCH SET j.run_at = CASE WHEN j.status = 'queued' THEN $run_at ELSE j.run_at END,
             j.payload = CASE WHEN j.status = 'queued' THEN $payload ELSE j.payload END
RETURN j.id AS id, j.status AS status, j.run_at AS run_at
