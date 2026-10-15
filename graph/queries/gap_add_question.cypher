// A question every leaver answers (rule M, from the policy) or one HR or the manager added
// (rule Q; a follow-up names the question it follows in `context`). Idempotent on the id.
MATCH (h:Handover {id: $handover})
MERGE (g:Gap {id: $id})
ON CREATE SET g.rule = $rule, g.target_id = $target, g.target_kind = 'Question', g.title = $title,
              g.seed = $question, g.question = $question, g.priority = $priority, g.status = 'open',
              g.created_at = $now, g.context = $context, g.asked_by = $by
MERGE (h)-[:HAS_GAP]->(g)
RETURN g.id AS id
