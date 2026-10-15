MATCH (g:Gap {id: $id})
SET g.question = $question
RETURN g.id AS id
