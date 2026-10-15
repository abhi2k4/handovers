MATCH (c:Connector {id: $id})
RETURN c.id AS id, c.status AS status, c.cursor AS cursor, c.last_sync AS last_sync,
       coalesce(c.active, false) AS active
