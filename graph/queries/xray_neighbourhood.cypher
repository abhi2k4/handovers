// Graph X-ray: a node and its direct neighbours, for the UI picture.
// Bookkeeping nodes are left out. Unless $self (the person viewing their own graph), items kept
// private (KNOWS {private: true}) and personal-sensitivity nodes are left out too.
// Structural neighbours (work, accounts, contacts, knowledge, team) come before raw sources.
MATCH (n {id: $id})
OPTIONAL MATCH (n)-[r]-(m)
WHERE NONE(l IN labels(m) WHERE l IN ['AuditEvent', 'Session', 'Turn'])
  AND ($self OR (coalesce(r.private, false) = false AND coalesce(m.sensitivity, '') <> 'personal'))
RETURN n.id AS id, labels(n) AS labels, coalesce(n.name, n.title, n.statement, n.id) AS label,
       type(r) AS rel, startNode(r).id AS rel_from,
       m.id AS mid, labels(m) AS mlabels, coalesce(m.name, m.title, m.statement, m.id) AS mlabel
ORDER BY CASE WHEN m IS NOT NULL AND 'Source' IN labels(m) THEN 1 ELSE 0 END
LIMIT $limit
