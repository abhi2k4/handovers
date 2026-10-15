// Reassign a leaver's sole-admin account (applied once HR approves): the new holder gets admin
// access now, the leaver keeps theirs until the last day ($leaver_until) so work does not lock
// mid-notice, and the handover's "only admin" gap (G7A) for that account is closed as reassigned.
// Nothing is deleted; access history stays.
MATCH (a:Account {id: $account})
MATCH (to:Employee {id: $to})
MERGE (to)-[ha:HAS_ACCESS]->(a)
ON CREATE SET ha.role = 'admin', ha.since = $now, ha.until = $open, ha.via = 'reassigned'
ON MATCH SET ha.role = 'admin', ha.until = CASE WHEN ha.until > $now THEN ha.until ELSE $open END
WITH a
OPTIONAL MATCH (:Handover {id: $handover})-[:FOR]->(leaver:Employee)-[la:HAS_ACCESS]->(a)
FOREACH (x IN CASE WHEN la IS NULL THEN [] ELSE [la] END |
  SET x.until = CASE WHEN x.until > $leaver_until THEN $leaver_until ELSE x.until END)
WITH a
OPTIONAL MATCH (:Handover {id: $handover})-[:HAS_GAP]->(g:Gap {rule: 'G7A', target_id: $account})
WITH a, collect(g) AS gaps
FOREACH (x IN gaps | SET x.status = 'dismissed', x.resolution = 'reassigned', x.resolved_at = $now)
RETURN a.id AS id, size(gaps) AS gaps
