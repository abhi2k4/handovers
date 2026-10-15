// Work records over a window, for the memory heatmap (bucketed by day in Python).
MATCH (s:Source)
WHERE s.occurred_at >= $from AND s.occurred_at <= $to
RETURN s.occurred_at AS at, s.kind AS kind
