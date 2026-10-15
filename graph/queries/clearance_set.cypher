// Move one clearance row: open, done (by its owner) or confirmed (by HR). Who marked it done and
// who confirmed it are kept apart, so the trail shows two people signed off.
MATCH (:Handover {id: $handover})-[:CLEARS]->(c:ClearanceItem {key: $key})
SET c.status = $status, c.by = $by, c.updated_at = $now,
    c.done_by = CASE WHEN $status = 'done' THEN $by WHEN $status = 'open' THEN null ELSE c.done_by END,
    c.confirmed_by = CASE WHEN $status = 'confirmed' THEN $by ELSE null END
RETURN c.id AS id, c.status AS status
