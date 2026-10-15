# app/backend/ingestion/

How anything becomes graph data: an upload, a connector record or a seed fixture.

| Module | What |
|---|---|
| `schema.py` | The closed ontology (`SourceIn`, `Fact`, ...): the only shapes that reach the graph |
| `pipeline.py` | Parse a file to text, extract facts (LLM or rules), resolve people, then write or queue for review |
| `writer.py` | The single graph writer: fixed, parameterised Cypher; confidence recomputed from evidence |

Facts the pipeline is not sure about wait in the review queue (Sources page) until someone
approves them. Knowledge is never overwritten: a newer fact supersedes the older one.
