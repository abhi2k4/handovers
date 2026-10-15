// A delivery channel's settings (WhatsApp), entered by the platform admin: encrypted values and
// the master switch that turns the channel off for everyone.
MATCH (c:Channel {id: $id})
RETURN c.config AS config, c.enabled AS enabled, c.updated_by AS updated_by, c.updated_at AS updated_at
