// The encrypted settings an admin entered for one connector (null when none).
MATCH (c:Connector {id: $id})
RETURN c.config AS config, c.configured_by AS configured_by, c.configured_at AS configured_at
