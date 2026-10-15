// The organisation's exit policy (one versioned node; see services/org_policy.py).
MATCH (p:Policy {id: $id})
RETURN p.rules_json AS rules_json, p.version AS version, p.updated_by AS updated_by,
       p.updated_at AS updated_at
