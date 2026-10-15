// The manager approves the draft ramp-up plan.
MATCH (p:RampPlan {status: 'draft'})-[:FROM]->(:Handover {id: $handover})
SET p.status = 'approved', p.approved_at = $now, p.approved_by = $by
RETURN p.id AS id
