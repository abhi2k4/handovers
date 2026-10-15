MATCH (s:Source)
WITH s.kind AS kind, count(s) AS n
RETURN kind, n
ORDER BY n DESC
