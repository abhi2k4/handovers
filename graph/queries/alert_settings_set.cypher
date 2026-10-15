// Save one person's alert settings (also the record of their WhatsApp opt-in).
MERGE (s:AlertSettings {employee: $emp})
SET s.phone = $phone, s.email = $email, s.modes = $modes, s.quiet_from = $quiet_from, s.quiet_to = $quiet_to,
    s.updated_at = $now
WITH s
OPTIONAL MATCH (e:Employee {id: $emp})
FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | MERGE (e)-[:WANTS_ALERTS]->(s))
RETURN s.employee AS employee
