MATCH (e:Employee {id: $emp})
CREATE (h:Handover {id: $id, status: 'pending', trigger: $trigger, created_at: $now,
                    effective_at: $effective_at, notice_days: $notice_days})
CREATE (h)-[:FOR]->(e)
RETURN h.id AS id
