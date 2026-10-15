MATCH (r:ReviewItem {status: 'pending'})
WITH count(r) AS n
RETURN n
