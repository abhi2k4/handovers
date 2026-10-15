MATCH (r:ReviewItem {id: $id})
SET r.status = $status, r.decided_at = $now
RETURN r.status AS status
