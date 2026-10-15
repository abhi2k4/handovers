// Newer knowledge replaces older; the older one is closed, never deleted.
MATCH (n:Knowledge {id: $new}), (o:Knowledge {id: $old})
MERGE (n)-[r:SUPERSEDES]->(o)
ON CREATE SET r.at = n.valid_from
SET o.valid_to = n.valid_from, o.status = 'superseded'
RETURN o.id AS id
