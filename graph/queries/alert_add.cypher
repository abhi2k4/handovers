// Record an alert (sent on WhatsApp, held for quiet hours, or shown in the app only).
CREATE (a:Alert {id: $id, kind: $kind, at: $now, to: $to, status: $status, title: $title,
                 body: $body, buttons: $buttons, href: $href, error: $error, step: $step})
WITH a
OPTIONAL MATCH (h:Handover {id: $handover})
FOREACH (_ IN CASE WHEN h IS NULL THEN [] ELSE [1] END | MERGE (a)-[:ABOUT]->(h))
WITH a
OPTIONAL MATCH (e:Employee {id: $to})
FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | MERGE (a)-[:SENT_TO]->(e))
RETURN a.id AS id
