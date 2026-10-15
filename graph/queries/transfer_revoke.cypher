// Revocation keeps lineage: edges are marked revoked, never deleted.
MATCH (s:Employee)-[kn:KNOWS]->(:Knowledge)
WHERE kn.transfer_id = $id
SET kn.revoked_at = $now
RETURN count(kn) AS revoked
