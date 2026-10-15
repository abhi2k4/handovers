// The employee keeps an item private: it never transfers and is never shown to others.
MATCH (:Employee {id: $emp})-[kn:KNOWS]->(k:Knowledge {id: $id})
SET kn.private = $private
RETURN k.id AS id, kn.private AS private
