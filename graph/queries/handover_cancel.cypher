// A withdrawn resignation: the handover stops, with who cancelled it and why. Nothing is deleted.
MATCH (h:Handover {id: $id})
WHERE NOT h.status IN ['cancelled', 'transferred']
SET h.status = 'cancelled', h.cancelled_at = $now, h.cancelled_by = $by, h.cancel_reason = $reason,
    h.updated_at = $now
RETURN h.id AS id
