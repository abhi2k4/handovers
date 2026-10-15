# graph/schema/

`indexes.cypher`: range and full-text indexes for the tenant graph, applied by
`python -m seed.load` and at startup when the graph is seeded. Idempotent. The model itself is
described in [docs/graph-model.md](../../docs/graph-model.md).
