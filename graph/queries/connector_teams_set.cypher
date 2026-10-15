// The teams a work-tool account serves (Sales Jira -> Sales). Replaces the previous set. Used to
// attribute its records to those teams: Source.origin is the account id.
MATCH (c:Connector {id: $id})
OPTIONAL MATCH (c)-[r:SERVES]->(:Team)
DELETE r
WITH DISTINCT c
UNWIND $teams AS tid
MATCH (t:Team {id: tid})
CREATE (c)-[:SERVES]->(t)
RETURN count(*) AS teams
