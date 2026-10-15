// Everything the leaver holds that could move; reasons are decided in services/transfer.py.
MATCH (e:Employee {id: $emp})-[kn:KNOWS]->(k:Knowledge)
WHERE k.retracted_at > $now AND kn.revoked_at IS NULL
OPTIONAL MATCH (succ:Employee {id: $successor})-[skn:KNOWS]->(k)
RETURN k.id AS id, k.kind AS kind, k.title AS title, k.sensitivity AS sensitivity,
       kn.private AS private, k.status AS status, k.confidence AS confidence,
       k.valid_to > $now AS current, skn IS NOT NULL AS already_held
