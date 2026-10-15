// A person from a directory or HR system, matched to an employee by email (created if new).
// Their team is set only when they have none yet, so a sync never moves someone silently.
MERGE (e:Employee {email: $email})
ON CREATE SET e.id = $id, e.joined_at = $now, e.status = $status, e.title = $title
SET e.name = $name,
    e.title = coalesce($title, e.title),
    e.status = CASE WHEN $status = 'departed' THEN 'departed' ELSE e.status END,
    e.directory = $system
WITH e
OPTIONAL MATCH (e)-[m:MEMBER_OF]->(:Team)
WITH e, count(m) AS teams
FOREACH (_ IN CASE WHEN teams = 0 AND $team <> '' THEN [1] ELSE [] END |
  MERGE (t:Team {id: $team})
  ON CREATE SET t.name = $department
  MERGE (e)-[:MEMBER_OF]->(t)
)
RETURN e.id AS id
