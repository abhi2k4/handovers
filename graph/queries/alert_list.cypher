// Alerts sent to one person, newest first, with the handover they are about.
MATCH (a:Alert {to: $to})
OPTIONAL MATCH (a)-[:ABOUT]->(h:Handover)
RETURN a.id AS id, a.kind AS kind, a.at AS at, a.status AS status, a.title AS title,
       a.body AS body, a.buttons AS buttons, a.href AS href, a.error AS error, a.acted AS acted,
       a.acted_at AS acted_at, h.id AS handover
ORDER BY at DESC
LIMIT 40
