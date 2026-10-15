// What someone does, ranked by how much of their logged work evidences it.
MATCH (e:Employee {id: $emp})-[rf:RESPONSIBLE_FOR]->(r:Responsibility)
WHERE rf.until > $now
OPTIONAL MATCH (o:Employee {status: 'active'})-[rf2:RESPONSIBLE_FOR]->(r)
WHERE o.id <> $emp AND rf2.until > $now AND coalesce(rf2.since, 0) <= $now
WITH e, rf, r, collect(DISTINCT o.name) AS co_owners
OPTIONAL MATCH (r)-[:EVIDENCED_BY]->(s:Source)-[:AUTHORED_BY]->(e)
WITH e, rf, r, co_owners, count(DISTINCT s) AS evidence, collect(DISTINCT s.kind) AS kinds
OPTIONAL MATCH (r)-[:EVIDENCED_BY]->(eod:EOD)-[:AUTHORED_BY]->(e)
WITH rf, r, co_owners, evidence, kinds, count(DISTINCT eod) AS eods
OPTIONAL MATCH (r)-[:ABOUT]->(a:Area)
WITH rf, r, co_owners, evidence, kinds, eods, collect(DISTINCT a.name) AS areas
OPTIONAL MATCH (r)-[:NEEDS_SKILL]->(k:Skill)
WITH rf, r, co_owners, evidence, kinds, eods, areas, collect(DISTINCT k.id) AS skill_ids,
     collect(DISTINCT k.name) AS skills
RETURN r.id AS id, r.title AS title, r.cadence AS cadence, rf.since AS since,
       rf.last_seen AS last_seen, rf.via AS via, co_owners, evidence, eods, kinds, areas,
       skill_ids, skills
ORDER BY evidence DESC
