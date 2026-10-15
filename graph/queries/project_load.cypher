// Project graph (handovers_project): load the architecture from graph/project/architecture.json.
// Components first, then the links between them, then the version that was loaded.
UNWIND $components AS c
CREATE (:Component {id: c.id, name: c.name, kind: c.kind, summary: c.summary, path: c.path})
WITH count(*) AS components
UNWIND $links AS l
MATCH (a:Component {id: l.from}), (b:Component {id: l.to})
CREATE (a)-[:USES {how: l.how}]->(b)
WITH components, count(*) AS links
CREATE (:ProjectMeta {version: $version})
RETURN components, links
