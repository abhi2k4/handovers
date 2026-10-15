// Skill or tool, with aliases used for resume matching.
MERGE (k:Skill {id: $id})
SET k.name = $name, k.category = $category, k.aliases = $aliases
RETURN k.id AS id
