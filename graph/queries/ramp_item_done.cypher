// The successor ticks an item of an approved plan (or unticks it: done_at removed).
MATCH (p:RampPlan {status: 'approved'})-[:HAS_ITEM]->(i:RampItem {id: $id})
SET i.done_at = CASE WHEN $done THEN $now ELSE null END
RETURN i.id AS id, i.done_at AS done_at
