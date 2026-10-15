MATCH (e:Employee {id: $id})
SET e.status = $status
RETURN e.status AS status
