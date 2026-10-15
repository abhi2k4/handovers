MATCH (:Handover {id: $handover})-[:HAS_TRANSFER]->(t:Transfer)
OPTIONAL MATCH (t)-[i:INCLUDED]->()
WITH t, count(i) AS included
OPTIONAL MATCH (t)-[x:EXCLUDED]->()
WITH t, included, count(x) AS excluded
OPTIONAL MATCH (t)-[:APPROVED_IN]->(ap:Approval)-[:BY]->(by:Employee)
RETURN t.id AS id, t.status AS status, t.planned_at AS planned_at, t.applied_at AS applied_at,
       ap.decision AS decision, ap.at AS approved_at, by.name AS approved_by, ap.comment AS comment,
       included, excluded
ORDER BY planned_at DESC
LIMIT 1
