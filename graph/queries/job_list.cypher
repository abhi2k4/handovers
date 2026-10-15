// The queue: what waits, what ran. Newest run time first.
MATCH (j:Job)
RETURN j.id AS id, j.key AS key, j.kind AS kind, j.status AS status, j.run_at AS run_at,
       j.attempts AS attempts, j.handover AS handover, j.finished_at AS finished_at,
       j.result AS result, j.last_error AS last_error
ORDER BY run_at DESC
LIMIT $limit
