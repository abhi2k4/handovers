// Project graph (handovers_project): the architecture version loaded last, to skip a reload.
MATCH (m:ProjectMeta)
RETURN m.version AS version
