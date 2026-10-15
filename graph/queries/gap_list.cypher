MATCH (:Handover {id: $handover})-[:HAS_GAP]->(g:Gap)
OPTIONAL MATCH (g)-[:RESOLVED_BY]->(a:Source)
RETURN g.id AS id, g.rule AS rule, g.target_id AS target_id, g.target_kind AS target_kind,
       g.title AS title, g.question AS question, g.seed AS seed, g.priority AS priority,
       g.status AS status, g.context AS context, g.resolution AS resolution, g.asked_by AS asked_by,
       a.id AS answer_id, a.text AS answer
ORDER BY priority DESC
