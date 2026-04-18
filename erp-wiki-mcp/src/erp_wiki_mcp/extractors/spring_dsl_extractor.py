"""Spring DSL extractor for resources.groovy beans."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_spring_dsl(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract Spring DSL bean definitions."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    beans = ast_node.get("beans", [])
    if not isinstance(beans, list):
        beans = [beans] if beans else []
    
    for bean in beans:
        bean_name = bean.get("name", "")
        class_name = bean.get("class_name", "")
        bean_line = bean.get("line", 0)
        
        bean_props = {
            "bean_name": bean_name,
            "class_name": class_name,
            "arguments": bean.get("args", []),
        }
        
        bean_node = Node(
            id=f"{project_id}:bean:{bean_name}",
            kind="bean",
            name=bean_name,
            fqn=class_name,
            file_path=file_path,
            line_start=bean_line,
            line_end=bean_line + 1,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=None,
            source_hash="",
            properties=bean_props,
            grails_version=None,
        )
        nodes.append(bean_node)
        
        # PROVIDES edge
        edges.append(RawEdge(
            source_id=bean_node.id,
            target_id="",
            target_hint=f"class:{class_name}",
            type="PROVIDES",
            file_path=file_path,
            line=bean_line,
            confidence="EXACT",
            extractor="spring_dsl_extractor",
        ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
