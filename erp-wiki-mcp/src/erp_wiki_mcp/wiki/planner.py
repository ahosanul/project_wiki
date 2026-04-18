"""Query planner for RAG pipeline."""

import re
from dataclasses import dataclass

from erp_wiki_mcp.embeddings.chunker import Chunk
from erp_wiki_mcp.embeddings.embedder import embed
from erp_wiki_mcp.embeddings.vector_store import SearchResult, VectorStore
from erp_wiki_mcp.graph.queries import GraphStore
from erp_wiki_mcp.registry.models import Node, RawEdge


@dataclass
class ContextPack:
    nodes: list[Node]
    edges: list[RawEdge]
    chunks: list[SearchResult]
    query_plan: list[str]
    intent: str


# Intent to query template mapping
INTENT_TEMPLATES = {
    "Location": ["find_symbol", "file_symbols"],
    "Logic": ["find_symbol", "callees_of", "renders_view"],
    "Impact": ["callers_of", "injected_into", "domain_relations"],
    "Trace": ["controller_flow", "callers_of", "callees_of", "renders_view"],
    "Relation": ["injects", "renders_view", "domain_relations", "controller_flow"],
    "Discovery": ["find_symbol"],
}


def extract_entities(question: str) -> dict:
    """Extract potential entities from question."""
    entities = {
        "symbol_names": [],
        "file_paths": [],
        "http_methods": [],
        "literals": [],
    }
    
    # CamelCase words → symbol names
    camel_case = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)*', question)
    entities["symbol_names"].extend(camel_case)
    
    # /path/ patterns → file paths
    paths = re.findall(r'/[\w/.-]+/', question)
    entities["file_paths"].extend(paths)
    
    # HTTP methods
    http_methods = re.findall(r'\b(GET|POST|PUT|DELETE|PATCH)\b', question, re.IGNORECASE)
    entities["http_methods"].extend(http_methods)
    
    # Quoted strings → literals
    literals = re.findall(r'"([^"]+)"|\'([^\']+)\'', question)
    entities["literals"].extend([l[0] or l[1] for l in literals])
    
    return entities


def plan(
    question: str,
    intent: str,
    project_id: str,
    graph_store: GraphStore,
    vector_store: VectorStore,
    max_depth: int = 3,
) -> ContextPack:
    """
    Build context pack for answering a question.
    
    1. Extract entities from question
    2. Select query templates based on intent
    3. Execute graph queries
    4. Run semantic search
    5. Merge results
    """
    entities = extract_entities(question)
    templates = INTENT_TEMPLATES.get(intent, ["find_symbol"])[:5]
    
    all_nodes: list[Node] = []
    all_edges: list[RawEdge] = []
    query_plan: list[str] = []
    
    # Execute graph queries
    for template in templates:
        args = {"pid": project_id}
        
        # Add entity-based filters
        if entities["symbol_names"]:
            args["q"] = entities["symbol_names"][0]
        
        try:
            result = graph_store.query(template, args)
            if result:
                nodes = result.get("nodes", [])
                edges = result.get("edges", [])
                all_nodes.extend(nodes)
                all_edges.extend(edges)
                query_plan.append(template)
        except Exception:
            pass
    
    # Semantic search
    chunks: list[SearchResult] = []
    try:
        question_embedding = embed([question])[0]
        search_results = vector_store.search(
            query_embedding=question_embedding,
            project_id=project_id,
            n_results=10,
        )
        chunks.extend(search_results)
    except Exception:
        pass
    
    # Deduplicate nodes by id
    seen_ids = set()
    unique_nodes = []
    for node in all_nodes:
        if node.id not in seen_ids:
            seen_ids.add(node.id)
            unique_nodes.append(node)
    
    # Cap results
    unique_nodes = unique_nodes[:50]
    all_edges = all_edges[:200]
    chunks = chunks[:50]
    
    return ContextPack(
        nodes=unique_nodes,
        edges=all_edges,
        chunks=chunks,
        query_plan=query_plan,
        intent=intent,
    )
