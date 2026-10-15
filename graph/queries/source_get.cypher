MATCH (s:Source {id: $id})
RETURN s.id AS id, s.kind AS kind, s.title AS title, s.text AS text, s.occurred_at AS occurred_at
