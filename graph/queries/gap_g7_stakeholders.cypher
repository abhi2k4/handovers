// G7 sole relationship: the leaver is the only contact for an external party.
MATCH (e:Employee {id: $emp})-[w:WORKS_WITH]->(st:Stakeholder)
WHERE w.until > $now
OPTIONAL MATCH (o:Employee {status: 'active'})-[w2:WORKS_WITH]->(st)
WHERE o.id <> $emp AND w2.until > $now
WITH st, w, count(o) AS others
WHERE others = 0
RETURN st.id AS target, st.name AS title, st.org AS org, st.kind AS kind, w.context AS context
