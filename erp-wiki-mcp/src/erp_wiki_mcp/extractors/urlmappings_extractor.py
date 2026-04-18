"""UrlMappings extractor for Grails URL mappings."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_urlmappings(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract URL mapping nodes and edges."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    # Look for mappings closure in AST
    mappings = ast_node.get("mappings", [])
    if not isinstance(mappings, list):
        mappings = [mappings] if mappings else []
    
    for mapping in mappings:
        http_method = mapping.get("http_method", "*")
        url_pattern = mapping.get("url_pattern", "")
        controller_hint = mapping.get("controller")
        action_hint = mapping.get("action")
        view_hint = mapping.get("view")
        named_mapping = mapping.get("name", "")
        
        mapping_line = mapping.get("line", 0)
        
        mapping_props = {
            "http_method": http_method,
            "url_pattern": url_pattern,
            "controller_hint": controller_hint,
            "action_hint": action_hint,
            "view_hint": view_hint,
            "named_mapping": named_mapping,
            "is_default": mapping.get("is_default", False),
        }
        
        mapping_id = f"{project_id}:url_mapping:{named_mapping or url_pattern}"
        
        mapping_node = Node(
            id=mapping_id,
            kind="url_mapping",
            name=named_mapping or url_pattern,
            fqn=url_pattern,
            file_path=file_path,
            line_start=mapping_line,
            line_end=mapping_line + 1,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=None,
            source_hash="",
            properties=mapping_props,
            grails_version=None,
        )
        nodes.append(mapping_node)
        
        # Emit MAPS_TO edge if controller/action specified
        if controller_hint or action_hint:
            target_hint = ""
            if controller_hint:
                target_hint += f"controller:{controller_hint}"
            if action_hint:
                target_hint += f",action:{action_hint}"
            
            edges.append(RawEdge(
                source_id=mapping_node.id,
                target_id="",
                target_hint=target_hint,
                type="MAPS_TO",
                file_path=file_path,
                line=mapping_line,
                confidence="UNRESOLVED",
                extractor="urlmappings_extractor",
            ))
        
        # Extract $varName params from pattern
        if "$" in url_pattern:
            import re
            params = re.findall(r'\$(\w+)', url_pattern)
            for param in params:
                param_node = Node(
                    id=f"{project_id}:url_param:{url_pattern}#{param}",
                    kind="url_param",
                    name=param,
                    fqn=f"{url_pattern}#{param}",
                    file_path=file_path,
                    line_start=mapping_line,
                    line_end=mapping_line,
                    language="groovy",
                    project_id=project_id,
                    last_run_id=last_run_id,
                    docstring=None,
                    source_hash="",
                    properties={"url_pattern": url_pattern},
                    grails_version=None,
                )
                nodes.append(param_node)
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
