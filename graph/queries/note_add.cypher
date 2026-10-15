// HR's (or the approver's) note on a handover: a remark, or a confirmation of something checked.
MATCH (h:Handover {id: $handover})
CREATE (n:Note {id: $id, kind: $kind, text: $text, by: $by, by_name: $by_name, at: $now})
CREATE (h)-[:HAS_NOTE]->(n)
RETURN n.id AS id
