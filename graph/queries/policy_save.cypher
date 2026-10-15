// Save the exit policy as a new version. Transfers and audit events name the version they used.
MERGE (p:Policy {id: $id})
ON CREATE SET p.version = 0
SET p.version = p.version + 1, p.rules_json = $rules, p.updated_by = $by, p.updated_at = $now
RETURN p.version AS version
