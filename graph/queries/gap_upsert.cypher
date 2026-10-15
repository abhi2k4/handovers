MATCH (h:Handover {id: $handover})
MERGE (g:Gap {id: $id})
ON CREATE SET g.rule = $rule, g.target_id = $target, g.target_kind = $target_kind, g.title = $title,
              g.seed = $seed, g.question = $question, g.priority = $priority, g.status = 'open',
              g.created_at = $now, g.context = $context
MERGE (h)-[:HAS_GAP]->(g)
RETURN g.id AS id
