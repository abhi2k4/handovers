// A held alert went out after quiet hours (or failed to).
MATCH (a:Alert {id: $id})
SET a.status = $status, a.error = $error, a.released_at = $now
RETURN a.id AS id
