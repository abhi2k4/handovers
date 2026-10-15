// The manager moves a draft item to another week or removes it.
MATCH (p:RampPlan {status: 'draft'})-[:HAS_ITEM]->(i:RampItem {id: $id})
SET i.week = coalesce($week, i.week), i.removed = coalesce($removed, i.removed)
RETURN i.id AS id, i.week AS week, i.removed AS removed
