// Area: what work is about (a service, a channel, a process, a client account).
MERGE (a:Area {id: $id})
SET a.name = $name, a.kind = $kind
RETURN a.id AS id
