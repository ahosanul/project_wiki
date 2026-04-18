"""Filters extractor for Grails 2.x filters."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_filters(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract Grails 2.x filter definitions."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    filters = ast_node.get("filters", [])
    if not isinstance(filters, list):
        filters = [filters] if filters else []
    
    for filt in filters:
        filter_name = filt.get("name", "")
        controller_pattern = filt.get("controller_pattern", "*")
        action_pattern = filt.get("action_pattern", "*")
        uri_pattern = filt.get("uri_pattern", "")
        filter_line = filt.get("line", 0)
        
        filter_props = {
            "name": filter_name,
            "controller_pattern": controller_pattern,
            "action_pattern": action_pattern,
            "uri_pattern": uri_pattern,
        }
        
        filter_node = Node(
            id=f"{project_id}:filter:{filter_name}",
            kind="grails_filters",
            name=filter_name,
            fqn=filter_name,
            file_path=file_path,
            line_start=filter_line,
            line_end=filter_line + 1,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=None,
            source_hash="",
            properties=filter_props,
            grails_version="2.x",
        )
        nodes.append(filter_node)
        
        # APPLIES_TO edge
        target_hint = ""
        if controller_pattern != "*":
            target_hint += f"controller:{controller_pattern}"
        if action_pattern != "*":
            target_hint += f",action:{action_pattern}"
        if uri_pattern:
            target_hint += f",uri:{uri_pattern}"
        
        edges.append(RawEdge(
            source_id=filter_node.id,
            target_id="",
            target_hint=target_hint,
            type="APPLIES_TO",
            file_path=file_path,
            line=filter_line,
            confidence="UNRESOLVED",
            extractor="filters_extractor",
        ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
