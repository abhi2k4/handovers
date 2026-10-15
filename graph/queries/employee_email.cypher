// Where an employee's email alerts go.
MATCH (e:Employee {id: $emp})
RETURN e.email AS email
