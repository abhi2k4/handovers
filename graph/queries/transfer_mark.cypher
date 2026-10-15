MATCH (t:Transfer {id: $id})
SET t.status = $status, t.applied_at = CASE WHEN $status = 'applied' THEN $now ELSE t.applied_at END
RETURN t.status AS status
