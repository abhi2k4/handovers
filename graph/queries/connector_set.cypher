// Record a sync run. The cursor only moves forward on success, so a failed run is retried in full.
MERGE (c:Connector {id: $id})
SET c.status = $status, c.last_sync = $now, c.error = $error,
    c.cursor = CASE WHEN $status = 'ok' THEN $cursor ELSE c.cursor END,
    c.sources = coalesce(c.sources, 0) + $sources,
    c.facts = coalesce(c.facts, 0) + $facts,
    c.review = coalesce(c.review, 0) + $review,
    c.people = coalesce(c.people, 0) + $people
RETURN c.id AS id
