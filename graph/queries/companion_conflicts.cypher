// Companion: live claims the asker holds that disagree with an answer candidate (same subject and
// predicate, different value, overlapping validity, neither supersedes the other). Same test as
// gap rule G6, limited to the asker's own memory.
MATCH (e:Employee {id: $emp})-[ka:KNOWS]->(a:Claim)
WHERE a.id IN $ids AND ka.revoked_at IS NULL AND a.valid_to > $now AND a.retracted_at > $now
MATCH (e)-[kb:KNOWS]->(b:Claim)
WHERE kb.revoked_at IS NULL AND b.subject = a.subject AND b.predicate = a.predicate
  AND b.id <> a.id AND b.value <> a.value AND b.valid_to > $now AND b.retracted_at > $now
  AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to
  AND NOT (a)-[:SUPERSEDES]-(b)
OPTIONAL MATCH (b)-[:EVIDENCED_BY]->(src:Source)
WITH a, b, collect(DISTINCT {id: src.id, kind: src.kind, title: src.title, at: src.occurred_at}) AS evidence
RETURN a.id AS claim, b.id AS id, b.kind AS kind, b.title AS title, b.value AS value,
       b.valid_from AS valid_from, evidence
