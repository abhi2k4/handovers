// Role (job family) that a JD describes.
MERGE (r:Role {id: $id})
SET r.title = $title
RETURN r.id AS id
