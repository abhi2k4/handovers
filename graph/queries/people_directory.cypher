// Closed-world roster for resolving names and emails in uploads.
MATCH (e:Employee)
RETURN e.id AS id, e.name AS name, e.email AS email, e.title AS title, e.status AS status
ORDER BY name
