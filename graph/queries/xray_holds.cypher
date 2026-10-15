// Graph X-ray access check: does this employee hold (KNOWS) this knowledge item?
MATCH (:Employee {id: $emp})-[k:KNOWS]->(x {id: $id})
RETURN count(k) AS n
