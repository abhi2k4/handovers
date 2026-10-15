// Match a signed-in identity to an employee. Departed people cannot sign in.
MATCH (e:Employee)
WHERE toLower(e.email) = $email AND e.status <> 'departed'
RETURN e.id AS id, e.name AS name
LIMIT 1
