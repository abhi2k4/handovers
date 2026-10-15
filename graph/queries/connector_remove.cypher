// Remove an extra account of a work tool (never a platform's first account, which is only
// cleared). Records it synced keep their origin; they are knowledge, never deleted.
MATCH (c:Connector {id: $id})
DETACH DELETE c
RETURN count(*) AS removed
