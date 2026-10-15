// G6 contradiction: two live claims about the same thing disagree and nothing resolves them.
MATCH (e:Employee {id: $emp})-[:KNOWS]->(a:Claim)
WHERE a.valid_to > $now AND a.retracted_at > $now
MATCH (b:Claim)
WHERE b.subject = a.subject AND b.predicate = a.predicate AND b.id <> a.id AND b.value <> a.value
  AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to AND b.retracted_at > $now
  AND NOT (a)-[:SUPERSEDES]-(b)
OPTIONAL MATCH (b)-[:EVIDENCED_BY]->(bs:Source)
WITH a, b, collect(DISTINCT bs.title) AS other_sources
RETURN a.id AS target, a.title AS title, a.value AS value, b.id AS other, b.title AS other_title,
       b.value AS other_value, other_sources
