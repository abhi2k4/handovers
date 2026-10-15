// Project graph (handovers_project) only: empty it before the architecture is loaded again.
// Matches only its own labels, so it can never touch a company graph by mistake.
MATCH (n)
WHERE n:Component OR n:ProjectMeta
DETACH DELETE n
RETURN count(*) AS deleted
