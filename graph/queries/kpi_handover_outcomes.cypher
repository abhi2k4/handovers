// Completed handovers: when the first transfer was applied (against the last day) and how much
// knowledge the successor received through approved transfers. Grouped by node only (FalkorDB 6.0.1).
MATCH (h:Handover {status: 'transferred'})-[:HAS_TRANSFER]->(t:Transfer {status: 'applied'})
OPTIONAL MATCH (t)-[:INCLUDED]->(k:Knowledge)
WITH h, min(t.applied_at) AS handed_at, count(DISTINCT k) AS knowledge
RETURN h.id AS id, h.effective_at AS effective_at, handed_at, knowledge
ORDER BY handed_at DESC
