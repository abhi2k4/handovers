// Store a connector's settings, encrypted by the backend before they get here. An empty value
// disconnects it, which also makes it inactive; the sync cursor is reset either way, so a new
// account is read from the start, and the last test result no longer applies.
// $id is an account: the platform id for its first account (`github`), `github:<slug>` for more.
MERGE (c:Connector {id: $id})
SET c.platform = $platform,
    c.label = CASE WHEN $config = '' THEN null ELSE coalesce($label, c.label) END,
    c.config = CASE WHEN $config = '' THEN null ELSE $config END,
    c.active = CASE WHEN $config = '' THEN false ELSE coalesce(c.active, false) END,
    c.configured_by = $by, c.configured_at = $now, c.cursor = null, c.status = null, c.error = null,
    c.test_ok = null, c.test_message = null, c.tested_at = null
RETURN c.id AS id
