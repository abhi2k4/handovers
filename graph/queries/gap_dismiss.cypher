// Drop a question from the exit interview, saying who did it and why (kept for the audit trail).
MATCH (g:Gap {id: $id})
SET g.status = 'dismissed', g.dismissed_by = $by, g.dismissed_at = $now, g.resolution = $reason
RETURN g.id AS id
