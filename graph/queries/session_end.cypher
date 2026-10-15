// Sign out everywhere: every session of this person ends (also the remedy for a leaked cookie).
MATCH (s:Session)-[:FOR]->({id: $employee})
DETACH DELETE s
RETURN count(*) AS ended
