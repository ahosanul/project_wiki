"""Graph query templates."""

TEMPLATES = {
    "find_symbol": """
        MATCH (s:Symbol {project_id: $pid})
        WHERE s.fqn CONTAINS $q OR s.name = $q
        RETURN s
        LIMIT 20
    """,
    "callers_of": """
        MATCH (a:Symbol)-[e:Edge {type: 'CALLS'}]->(b:Symbol {id: $id})
        RETURN a, e
        LIMIT 50
    """,
    "callees_of": """
        MATCH (a:Symbol {id: $id})-[e:Edge {type: 'CALLS'}]->(b:Symbol)
        RETURN b, e
        LIMIT 50
    """,
    "file_symbols": """
        MATCH (s:Symbol {file_path: $fp, project_id: $pid})
        RETURN s
    """,
    "injects": """
        MATCH (a:Symbol {id: $id})-[e:Edge {type: 'INJECTS'}]->(b:Symbol)
        RETURN b, e
    """,
    "extends": """
        MATCH (a:Symbol {id: $id})-[e:Edge {type: 'EXTENDS'}]->(b:Symbol)
        RETURN b, e
    """,
    "implements": """
        MATCH (a:Symbol {id: $id})-[e:Edge {type: 'IMPLEMENTS'}]->(b:Symbol)
        RETURN b, e
    """,
    "declares": """
        MATCH (a:Symbol {id: $id})-[e:Edge {type: 'DECLARES'}]->(b:Symbol)
        RETURN b, e
    """,
}


def get_template(name: str) -> str | None:
    """Get a query template by name."""
    return TEMPLATES.get(name)


def list_templates() -> list[str]:
    """List all available query templates."""
    return list(TEMPLATES.keys())
