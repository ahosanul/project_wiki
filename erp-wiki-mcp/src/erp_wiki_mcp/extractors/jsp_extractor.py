"""JSP extractor for JavaServer Pages."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_jsp(parse_result: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract JSP-specific nodes and edges."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    # Determine kind from path
    if "/includes/" in file_path or file_path.endswith(".jspf"):
        kind = "jsp_include"
    else:
        kind = "jsp_view"
    
    includes = parse_result.get("includes", [])
    forwards = parse_result.get("forwards", [])
    taglibs = parse_result.get("taglibs", [])
    
    jsp_props = {
        "includes": includes,
        "forwards": forwards,
        "taglibs": taglibs,
    }
    
    jsp_node = Node(
        id=f"{project_id}:jsp:{file_path}",
        kind=kind,
        name=file_path.split("/")[-1],
        fqn=file_path,
        file_path=file_path,
        line_start=0,
        line_end=0,
        language="jsp",
        project_id=project_id,
        last_run_id=last_run_id,
        docstring=None,
        source_hash="",
        properties=jsp_props,
        grails_version=None,
    )
    nodes.append(jsp_node)
    
    # JSP_INCLUDES edges
    for inc in includes:
        edges.append(RawEdge(
            source_id=jsp_node.id,
            target_id="",
            target_hint=f"include:{inc}",
            type="JSP_INCLUDES",
            file_path=file_path,
            line=0,
            confidence="UNRESOLVED",
            extractor="jsp_extractor",
        ))
    
    # JSP_FORWARDS edges
    for fwd in forwards:
        edges.append(RawEdge(
            source_id=jsp_node.id,
            target_id="",
            target_hint=f"forward:{fwd}",
            type="JSP_FORWARDS",
            file_path=file_path,
            line=0,
            confidence="UNRESOLVED",
            extractor="jsp_extractor",
        ))
    
    # USES_TAGLIB edges
    for taglib in taglibs:
        uri = taglib.get("uri", "")
        prefix = taglib.get("prefix", "")
        edges.append(RawEdge(
            source_id=jsp_node.id,
            target_id="",
            target_hint=f"taglib:{prefix}:{uri}",
            type="USES_TAGLIB",
            file_path=file_path,
            line=0,
            confidence="UNRESOLVED",
            extractor="jsp_extractor",
        ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
