// A decision, procedure or claim. Bi-temporal; KNOWS edges record who holds it.
// {label} is one of Decision, Procedure, Claim.
MATCH (s:Source {id: $source})
MERGE (k:Knowledge:{label} {id: $key})
ON CREATE SET k.kind = $kind, k.title = $title, k.status = 'confirmed', k.valid_from = $valid_from,
              k.valid_to = $open, k.recorded_at = $now, k.retracted_at = $open,
              k.sensitivity = $sensitivity, k.confidence = 0.0, k.sources = 0, k.origin = $origin
SET k.rationale = coalesce($rationale, k.rationale),
    k.alternatives = CASE WHEN size($alternatives) > 0 THEN $alternatives ELSE k.alternatives END,
    k.steps = CASE WHEN size($steps) > 0 THEN $steps ELSE k.steps END,
    k.handles = coalesce($handles, k.handles),
    k.subject = coalesce($subject, k.subject),
    k.predicate = coalesce($predicate, k.predicate),
    k.value = coalesce($value, k.value),
    k.text = CASE WHEN k.text IS NULL OR size($text) > size(k.text) THEN $text ELSE k.text END,
    k.sensitivity = CASE WHEN $sensitivity = 'personal' THEN 'personal' ELSE k.sensitivity END
MERGE (k)-[ev:EVIDENCED_BY]->(s)
SET ev.quote = $quote
FOREACH (aid IN $areas | MERGE (a:Area {id: aid}) MERGE (k)-[:ABOUT]->(a))
FOREACH (_ IN CASE WHEN $documented THEN [1] ELSE [] END | MERGE (k)-[:DOCUMENTED_IN]->(s))
WITH k
UNWIND $people AS pid
MATCH (e:Employee {id: pid})
MERGE (e)-[kn:KNOWS]->(k)
ON CREATE SET kn.via = 'observed', kn.since = $occurred_at, kn.private = false
RETURN count(kn) AS linked
