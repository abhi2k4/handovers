// Candidates for a handover's vacancy, in import order, with per-criterion verdicts (JSON).
MATCH (:Handover {id: $handover})-[:HAS_CANDIDATE]->(c:Candidate)
RETURN c.id AS id, c.name AS name, c.phone AS phone, c.city AS city, c.summary AS summary,
       c.source AS source, c.must_met AS must_met, c.must_total AS must_total,
       c.verdicts AS verdicts, c.created_at AS created_at
ORDER BY created_at DESC, name
