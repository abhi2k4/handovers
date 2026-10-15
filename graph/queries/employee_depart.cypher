// Mark someone as gone on their last day (they can no longer sign in).
MATCH (e:Employee {id: $id})
WHERE e.status <> 'departed'
SET e.status = 'departed', e.departed_at = $now
RETURN e.id AS id
