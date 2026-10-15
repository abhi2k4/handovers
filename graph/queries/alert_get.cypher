// One alert, for acting on a button tap.
MATCH (a:Alert {id: $id})
OPTIONAL MATCH (a)-[:ABOUT]->(h:Handover)
RETURN a.id AS id, a.kind AS kind, a.to AS to, a.status AS status, a.buttons AS buttons,
       a.acted AS acted, h.id AS handover
