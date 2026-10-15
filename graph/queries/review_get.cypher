MATCH (r:ReviewItem {id: $id})
RETURN r.id AS id, r.source_id AS source_id, r.fact AS fact, r.status AS status
