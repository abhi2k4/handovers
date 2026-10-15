// People joining, and whose work they inherit (if a handover names them).
MATCH (e:Employee {status: 'incoming'})-[:MEMBER_OF]->(t:Team)
OPTIONAL MATCH (h:Handover)-[:SUCCESSOR]->(e)
OPTIONAL MATCH (h)-[:FOR]->(l:Employee)
RETURN e.id AS id, e.name AS name, e.title AS title, e.joined_at AS starts, t.name AS team,
       h.id AS handover_id, l.name AS inherits_from
ORDER BY starts
