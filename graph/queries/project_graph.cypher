// Project graph (handovers_project): every component and every link, for the "How it's built" view.
MATCH (c:Component)
WITH collect({id: c.id, name: c.name, kind: c.kind, summary: c.summary, path: c.path}) AS nodes
OPTIONAL MATCH (a:Component)-[r:USES]->(b:Component)
RETURN nodes, collect({source: a.id, target: b.id, how: r.how}) AS links
