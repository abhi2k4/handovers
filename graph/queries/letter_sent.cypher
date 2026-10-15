// The relieving letter went out (HR's final sign-off on the exit).
MATCH (h:Handover {id: $id})
SET h.letter_sent_at = $now, h.letter_sent_by = $by, h.letter_subject = $subject, h.letter_to = $to
RETURN h.id AS id
