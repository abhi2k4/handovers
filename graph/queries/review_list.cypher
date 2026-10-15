MATCH (r:ReviewItem {status: 'pending'})
OPTIONAL MATCH (s:Source {id: r.source_id})
RETURN r.id AS id, r.kind AS kind, r.title AS title, r.confidence AS confidence,
       r.employee AS employee, r.fact AS fact, s.title AS source
ORDER BY r.created_at DESC
