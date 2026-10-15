// Low-confidence extracted facts wait here for a human; they are not in the graph yet.
CREATE (r:ReviewItem {id: $id, source_id: $source, fact: $fact, kind: $kind, title: $title,
                      confidence: $confidence, employee: $employee, status: 'pending',
                      created_at: $now})
RETURN r.id AS id
