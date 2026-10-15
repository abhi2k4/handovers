// Immutable evidence. {label} is a whitelisted source kind (EOD, PullRequest, Document, ...).
MERGE (s:Source:{label} {id: $id})
SET s.kind = $kind, s.system = $system, s.title = $title, s.text = $text,
    s.occurred_at = $occurred_at, s.sensitivity = $sensitivity, s.quality = $quality,
    s.url = $url, s.status = $status, s.doc_type = $doc_type, s.origin = $origin,
    s.ingested_at = $now
FOREACH (aid IN $areas | MERGE (a:Area {id: aid}) MERGE (s)-[:ABOUT]->(a))
FOREACH (sid IN $skills | MERGE (k:Skill {id: sid}) MERGE (s)-[:SHOWS_SKILL]->(k))
WITH s
OPTIONAL MATCH (au:Employee {id: $author})
FOREACH (_ IN CASE WHEN au IS NULL THEN [] ELSE [1] END | MERGE (s)-[:AUTHORED_BY]->(au))
RETURN s.id AS id
