MATCH (h:Handover {id: $id})-[:FOR]->(e:Employee)
OPTIONAL MATCH (e)-[:MEMBER_OF]->(t:Team)
OPTIONAL MATCH (e)-[:REPORTS_TO]->(m:Employee)
OPTIONAL MATCH (h)-[:SUCCESSOR]->(s:Employee)
RETURN h.id AS id, h.status AS status, h.trigger AS trigger, h.created_at AS created_at,
       h.effective_at AS effective_at, h.notice_days AS notice_days, e.id AS employee_id,
       e.name AS employee, e.title AS title, t.name AS team, m.id AS manager_id, m.name AS manager,
       s.id AS successor_id, s.name AS successor, s.title AS successor_title,
       h.cancelled_at AS cancelled_at, h.cancelled_by AS cancelled_by, h.cancel_reason AS cancel_reason,
       h.letter_sent_at AS letter_sent_at, h.letter_sent_by AS letter_sent_by,
       e.email AS employee_email, e.status AS employee_status, t.id AS team_id
