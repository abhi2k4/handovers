// Store imported job-board candidates for a handover's vacancy (re-import updates, never duplicates).
MATCH (h:Handover {id: $handover})
UNWIND $rows AS r
MERGE (c:Candidate {id: r.id})
ON CREATE SET c.created_at = $now
SET c.name = r.name, c.phone = r.phone, c.city = r.city, c.summary = r.summary,
    c.source = r.source, c.must_met = r.must_met, c.must_total = r.must_total,
    c.verdicts = r.verdicts, c.updated_at = $now
MERGE (h)-[:HAS_CANDIDATE]->(c)
RETURN c.id AS id
