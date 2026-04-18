"""Bootstrap extractor for BootStrap.groovy."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_bootstrap(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract Bootstrap initialization information."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    for cls in ast_node.get("classes", []):
        class_name = cls.get("name", "BootStrap")
        class_line = cls.get("line", 0)
        
        has_init = False
        has_destroy = False
        
        for method in cls.get("methods", []):
            if method.get("name") == "init":
                has_init = True
            elif method.get("name") == "destroy":
                has_destroy = True
        
        bootstrap_props = {
            "has_init": has_init,
            "has_destroy": has_destroy,
        }
        
        bootstrap_node = Node(
            id=f"{project_id}:bootstrap:BootStrap",
            kind="bootstrap",
            name="BootStrap",
            fqn="BootStrap",
            file_path=file_path,
            line_start=class_line,
            line_end=class_line + 1,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=cls.get("docstring"),
            source_hash="",
            properties=bootstrap_props,
            grails_version=None,
        )
        nodes.append(bootstrap_node)
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
