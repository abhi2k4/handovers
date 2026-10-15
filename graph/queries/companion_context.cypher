// Evidence, the decision behind it, and what it replaced, for knowledge the person holds.
MATCH (:Employee {id: $emp})-[kn:KNOWS]->(k:Knowledge)
WHERE k.id IN $ids AND kn.revoked_at IS NULL
OPTIONAL MATCH (k)-[ev:EVIDENCED_BY]->(src:Source)
OPTIONAL MATCH (src)-[:AUTHORED_BY]->(au:Employee)
WITH kn, k, collect(DISTINCT {id: src.id, kind: src.kind, title: src.title, at: src.occurred_at,
                              author: au.name, quote: ev.quote}) AS evidence
// The reason: a decision it is JUSTIFIED_BY, or the leaver's answer that CONFIRMS it as current
// ("sources disagree", settled in the exit interview).
OPTIONAL MATCH (k)-[:JUSTIFIED_BY|CONFIRMS]-(dd:Decision)
WITH kn, k, evidence, head(collect(dd)) AS d
OPTIONAL MATCH (k)-[:SUPERSEDES]->(prev:Knowledge)
OPTIONAL MATCH (from:Employee {id: kn.from_id})
OPTIONAL MATCH (ap:Approval {id: kn.approval_id})-[:BY]->(approver:Employee)
RETURN k.id AS id, k.kind AS kind, k.title AS title, k.rationale AS rationale, k.value AS value,
       k.steps AS steps, k.valid_from AS valid_from, k.valid_to AS valid_to,
       k.confidence AS confidence, kn.via AS via, from.name AS from_name, ap.at AS approved_at,
       approver.name AS approved_by, evidence, d.id AS decision_id, d.title AS decision,
       d.rationale AS decision_rationale, prev.value AS previous_value, prev.title AS previous_title
