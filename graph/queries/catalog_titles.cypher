// Existing responsibilities, accounts and stakeholders, for matching extracted titles to known ids.
MATCH (r:Responsibility) RETURN r.id AS id, r.title AS title, 'Responsibility' AS kind
UNION
MATCH (a:Account) RETURN a.id AS id, a.name AS title, 'Account' AS kind
UNION
MATCH (s:Stakeholder) RETURN s.id AS id, s.name AS title, 'Stakeholder' AS kind
UNION
MATCH (k:Knowledge) RETURN k.id AS id, k.title AS title, 'Knowledge' AS kind
