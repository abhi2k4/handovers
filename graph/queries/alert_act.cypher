// Record which button was tapped on an alert.
MATCH (a:Alert {id: $id})
SET a.acted = $acted, a.acted_at = $now
RETURN a.id AS id
