// Store a delivery channel's settings (encrypted by the backend) and/or its master switch.
// A null leaves that part as it was.
MERGE (c:Channel {id: $id})
SET c.config = coalesce($config, c.config),
    c.enabled = coalesce($enabled, c.enabled),
    c.updated_by = $by, c.updated_at = $now
RETURN c.id AS id
