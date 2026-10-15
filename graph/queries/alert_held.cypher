// Alerts held back during someone's quiet hours and not yet delivered.
MATCH (a:Alert {status: 'held'})
WHERE a.acted IS NULL
RETURN a.id AS id, a.kind AS kind, a.to AS to, a.title AS title, a.body AS body,
       a.buttons AS buttons, a.href AS href
ORDER BY a.at
LIMIT 200
