// Open a handover, unless this person already has a live one (same rule as
// handover_open_for_employee). Check and create are one statement, so two clicks at once
// cannot open two handovers: FalkorDB runs writes to a graph one at a time.
MATCH (e:Employee {id: $emp})
OPTIONAL MATCH (live:Handover)-[:FOR]->(e)
WHERE live.status IN ['pending', 'analyzing', 'interview', 'review', 'approved']
   OR (live.status = 'transferred' AND e.status <> 'departed')
WITH e, count(live) AS open
WHERE open = 0
CREATE (h:Handover {id: $id, status: 'pending', trigger: $trigger, created_at: $now,
                    effective_at: $effective_at, notice_days: $notice_days})
CREATE (h)-[:FOR]->(e)
RETURN h.id AS id
