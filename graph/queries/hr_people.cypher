// Active people who are HR under the organisation's policy: a team (id or name) in $teams, or a
// sign-in group in $teams or mapped to hr in $groups. Names are compared in lower case.
MATCH (e:Employee {status: 'active'})
OPTIONAL MATCH (e)-[:MEMBER_OF]->(t:Team)
WITH e, t
WHERE toLower(coalesce(t.id, '')) IN $teams OR toLower(coalesce(t.name, '')) IN $teams
   OR any(g IN coalesce(e.groups, []) WHERE toLower(g) IN $teams OR toLower(g) IN $groups)
RETURN DISTINCT e.id AS id, e.name AS name, e.title AS title
ORDER BY name
