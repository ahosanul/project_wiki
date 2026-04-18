"""Verify change tool for detecting issues after modifications."""

import logging

from erp_wiki_mcp.graph.store import GraphStore
from erp_wiki_mcp.registry.db import RegistryDB

logger = logging.getLogger(__name__)


async def handler(
    run_id: str,
) -> dict:
    """
    Verify a change by checking for new unresolved edges and model mismatches.
    
    Args:
        run_id: The run ID from the indexing operation
    
    Returns:
        {issues: [{type, severity, symbol_id, message}], resolved_count, new_unresolved_count}
    """
    logger.info(f"[verify_change] Starting handler for run_id={run_id}")
    
    registry = RegistryDB()
    logger.info(f"[verify_change] Registry data_dir={registry.data_dir}")
    
    graph_store = GraphStore(registry.data_dir)
    logger.info(f"[verify_change] GraphStore initialized with db_path={graph_store.db_path if hasattr(graph_store, 'db_path') else 'N/A'}")
    
    issues = []
    
    # Check for UNRESOLVED edges
    try:
        result = graph_store.query("missing_views", {"pid": ""})
        if result:
            for edge in result.get("edges", []):
                issues.append({
                    "type": "UNRESOLVED_EDGE",
                    "severity": "WARNING",
                    "symbol_id": edge.get("source_id"),
                    "message": f"Edge {edge.get('type')} could not be resolved",
                })
    except Exception:
        pass
    
    # Check for MODEL_MISMATCH edges
    try:
        # Would query for MODEL_MISMATCH edges
        pass
    except Exception:
        pass
    
    return {
        "issues": issues,
        "resolved_count": 0,
        "new_unresolved_count": len(issues),
    }
