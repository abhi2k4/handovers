// The account is one the leaver of this handover holds (any role). Reassignment is only for
// the leaver's own accounts, never an arbitrary account picked by id.
MATCH (:Handover {id: $handover})-[:FOR]->(:Employee)-[:HAS_ACCESS]->(a:Account {id: $account})
RETURN a.id AS id
LIMIT 1
