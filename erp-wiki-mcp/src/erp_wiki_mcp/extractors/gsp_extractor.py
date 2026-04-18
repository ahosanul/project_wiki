"""GSP extractor for Grails Server Pages."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_gsp(parse_result: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract GSP-specific nodes and edges."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    # Determine kind from path
    if "/layouts/" in file_path:
        kind = "gsp_layout"
    elif "/_" in file_path.split("/")[-1]:
        kind = "gsp_template"
    else:
        kind = "gsp_view"
    
    layout = parse_result.get("layout", "")
    model_variables = parse_result.get("model_variables", [])
    expressions = parse_result.get("expressions", [])
    includes = parse_result.get("includes", [])
    tags_used = parse_result.get("tags_used", [])
    static_text = parse_result.get("static_text", "")
    
    gsp_props = {
        "layout": layout,
        "model_variables": model_variables,
        "expressions": expressions,
        "includes": includes,
        "tags_used": tags_used,
        "static_text": static_text[:500] if static_text else "",  # Truncate
    }
    
    gsp_node = Node(
        id=f"{project_id}:gsp:{file_path}",
        kind=kind,
        name=file_path.split("/")[-1],
        fqn=file_path,
        file_path=file_path,
        line_start=0,
        line_end=0,
        language="gsp",
        project_id=project_id,
        last_run_id=last_run_id,
        docstring=None,
        source_hash="",
        properties=gsp_props,
        grails_version=None,
    )
    nodes.append(gsp_node)
    
    # USES_LAYOUT edge
    if layout:
        edges.append(RawEdge(
            source_id=gsp_node.id,
            target_id="",
            target_hint=f"layout:{layout}",
            type="USES_LAYOUT",
            file_path=file_path,
            line=0,
            confidence="UNRESOLVED",
            extractor="gsp_extractor",
        ))
    
    # INCLUDES_TEMPLATE edges
    for inc in includes:
        edges.append(RawEdge(
            source_id=gsp_node.id,
            target_id="",
            target_hint=f"template:{inc}",
            type="INCLUDES_TEMPLATE",
            file_path=file_path,
            line=0,
            confidence="UNRESOLVED",
            extractor="gsp_extractor",
        ))
    
    # LINKS_TO edges (simplified - would need actual link analysis)
    # USES_TAG edges
    for tag in tags_used:
        if ":" in tag:
            ns, name = tag.split(":", 1)
            edges.append(RawEdge(
                source_id=gsp_node.id,
                target_id="",
                target_hint=f"tag:{ns}:{name}",
                type="USES_TAG",
                file_path=file_path,
                line=0,
                confidence="UNRESOLVED",
                extractor="gsp_extractor",
            ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
