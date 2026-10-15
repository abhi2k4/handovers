// Make a connector inactive: it keeps its settings but is not synced until made active again.
MATCH (c:Connector {id: $id})
SET c.active = false
RETURN c.id AS id
