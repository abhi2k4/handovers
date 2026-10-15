// When each readiness step of a handover was last reminded.
MATCH (a:Alert)-[:ABOUT]->(:Handover {id: $handover})
WHERE a.step IS NOT NULL
RETURN a.step AS step, max(a.at) AS at
