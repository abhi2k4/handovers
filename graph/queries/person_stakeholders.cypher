MATCH (e:Employee {id: $emp})-[w:WORKS_WITH]->(st:Stakeholder)
WHERE w.until > $now
OPTIONAL MATCH (o:Employee {status: 'active'})-[w2:WORKS_WITH]->(st)
WHERE o.id <> $emp AND w2.until > $now AND coalesce(w2.since, 0) <= $now
WITH st, w, collect(DISTINCT o.name) AS other_contacts
RETURN st.id AS id, st.name AS name, st.org AS org, st.kind AS kind, w.context AS context,
       w.touches AS touches, w.last_seen AS last_seen, other_contacts
ORDER BY touches DESC
