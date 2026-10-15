// When the handover's first transfer was applied (follow-ups come later); null if none yet.
MATCH (:Handover {id: $handover})-[:HAS_TRANSFER]->(t:Transfer {status: 'applied'})
RETURN min(t.applied_at) AS at
