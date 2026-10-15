// The platform operator (the Handovers team account): not an employee, so it has no team, work or
// knowledge, only sessions. Created or renamed at startup.
MERGE (o:Operator {id: $id})
SET o.name = $name, o.email = $email
RETURN o.id AS id
