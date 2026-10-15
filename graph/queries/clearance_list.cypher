// The clearance (no-dues) rows of a handover, in order, with who last changed them.
MATCH (:Handover {id: $handover})-[:CLEARS]->(c:ClearanceItem)
RETURN c.id AS id, c.key AS key, c.label AS label, c.group AS group, c.owner AS owner,
       c.target AS target, c.status AS status, c.by AS by, c.updated_at AS updated_at
ORDER BY c.ord
