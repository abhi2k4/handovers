MATCH (h:Handover {id: $id})
SET h.status = $status, h.updated_at = $now
RETURN h.status AS status
