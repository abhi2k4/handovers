// The result of the last Test of a connector's saved settings, shown on its card.
MERGE (c:Connector {id: $id})
SET c.test_ok = $ok, c.test_message = $message, c.tested_at = $now
RETURN c.id AS id
