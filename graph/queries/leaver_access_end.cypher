// The leaver's last day: every access they still hold ends now (history kept, never deleted).
MATCH (e:Employee {id: $emp})-[ha:HAS_ACCESS]->(:Account)
WHERE ha.until > $now
SET ha.until = $now, ha.ended_by = 'last day'
RETURN count(ha) AS ended
