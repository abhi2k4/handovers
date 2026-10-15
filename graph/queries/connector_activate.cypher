// Make one connector the active one in its category (a directory): every other connector named
// in $ids becomes inactive in the same write, so two can never be active at once. Their
// settings are kept, so switching back needs no re-entry.
UNWIND $ids AS cid
MERGE (c:Connector {id: cid})
SET c.active = (cid = $id),
    c.activated_at = CASE WHEN cid = $id THEN $now ELSE c.activated_at END
RETURN c.id AS id, c.active AS active
