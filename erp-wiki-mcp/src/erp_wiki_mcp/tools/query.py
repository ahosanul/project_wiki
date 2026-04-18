"""Query tool for graph queries."""

import logging

from erp_wiki_mcp.graph.queries import get_template, list_templates
from erp_wiki_mcp.graph.store import GraphStore

logger = logging.getLogger(__name__)


async def query_graph(
    store: GraphStore,
    project_id: str,
    template: str,
    args: dict | None = None,
) -> dict:
    """
    Execute a graph query using a named template.

    Args:
        store: Graph store connection
        project_id: Project identifier
        template: Query template name
        args: Additional query arguments

    Returns:
        Dict with nodes and edges lists
    """
    query = get_template(template)
    if not query:
        available = ", ".join(list_templates())
        raise ValueError(f"Unknown template: {template}. Available: {available}")

    # Build parameters
    params = {"pid": project_id, **(args or {})}

    try:
        result = store.execute(query, params)

        nodes = []
        edges = []

        while result.has_next():
            row = result.get_next()
            for value in row.values:
                if hasattr(value, "_value"):
                    obj = value._value
                    if isinstance(obj, dict):
                        if "id" in obj and ("kind" in obj or "fqn" in obj):
                            # This is a Symbol node
                            nodes.append(obj)
                        elif "type" in obj and ("confidence" in obj or "source_id" in obj):
                            # This is an Edge
                            edges.append(obj)

        return {"nodes": nodes, "edges": edges, "template": template}

    except Exception as e:
        logger.exception(f"Query failed: {e}")
        raise
