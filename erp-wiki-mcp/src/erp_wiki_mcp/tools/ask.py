"""Ask tool for natural language Q&A."""

import logging

from erp_wiki_mcp.embeddings.embedder import embed
from erp_wiki_mcp.graph.store import GraphStore
from erp_wiki_mcp.registry.db import RegistryDB
from erp_wiki_mcp.wiki.planner import plan
from erp_wiki_mcp.wiki.router import classify_intent

logger = logging.getLogger(__name__)


async def handler(
    project_id: str,
    question: str,
    max_depth: int = 3,
) -> dict:
    """
    Answer a natural language question about the codebase.
    
    Args:
        project_id: Project identifier
        question: Natural language question
        max_depth: Max graph traversal depth
    
    Returns:
        {answer, context_nodes[], context_edges[], chunks[], intent, query_plan[]}
    """
    logger.info(f"[ask] Starting handler for project_id={project_id}, question={question[:50]}...")
    
    registry = RegistryDB()
    logger.info(f"[ask] Registry data_dir={registry.data_dir}")
    
    graph_store = GraphStore(registry.data_dir)
    logger.info(f"[ask] GraphStore initialized with db_path={graph_store.db_path if hasattr(graph_store, 'db_path') else 'N/A'}")
    
    vector_store = None  # Would initialize from config
    logger.info(f"[ask] Vector store initialized: {vector_store is not None}")
    
    # Classify intent
    intent = classify_intent(question)
    
    # Build context pack
    try:
        context_pack = plan(
            question=question,
            intent=intent,
            project_id=project_id,
            graph_store=graph_store,
            vector_store=vector_store,
            max_depth=max_depth,
        )
    except Exception as e:
        return {
            "error": str(e),
            "intent": intent,
            "context_nodes": [],
            "context_edges": [],
            "chunks": [],
            "query_plan": [],
        }
    
    # Format answer (simplified - would use LLM in production)
    nodes_summary = [f"{n.kind}:{n.name}" for n in context_pack.nodes[:10]]
    edges_summary = [f"{e.type}" for e in context_pack.edges[:10]]
    
    answer = f"Found {len(context_pack.nodes)} symbols and {len(context_pack.edges)} relationships.\n\n"
    answer += f"Intent: {intent}\n"
    answer += f"Query plan: {', '.join(context_pack.query_plan)}\n\n"
    answer += "Symbols:\n" + "\n".join(nodes_summary) + "\n\n"
    answer += "Relationships:\n" + "\n".join(edges_summary)
    
    return {
        "answer": answer,
        "context_nodes": [n.model_dump() for n in context_pack.nodes],
        "context_edges": [e.model_dump() for e in context_pack.edges],
        "chunks": [
            {"symbol_id": c.symbol_id, "text": c.text[:200], "distance": c.distance}
            for c in context_pack.chunks
        ],
        "intent": intent,
        "query_plan": context_pack.query_plan,
    }
