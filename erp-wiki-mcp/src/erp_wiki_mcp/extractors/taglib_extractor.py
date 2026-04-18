"""Taglib extractor for Grails tag libraries."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_taglib(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract taglib-specific nodes and edges."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        class_name = cls.get("name", "")
        class_line = cls.get("line", 0)
        class_end_line = cls.get("endLine", class_line + 1)
        
        # Extract namespace
        namespace = "g"
        for field in cls.get("fields", []):
            if field.get("name") == "namespace":
                namespace = field.get("value", "g")
        
        taglib_props = {
            "namespace": namespace,
            "is_taglib": True,
        }
        
        taglib_node = Node(
            id=f"{project_id}:taglib:{class_fqn}",
            kind="tag_lib",
            name=class_name,
            fqn=class_fqn,
            file_path=file_path,
            line_start=class_line,
            line_end=class_end_line,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=cls.get("docstring"),
            source_hash="",
            properties=taglib_props,
            grails_version=None,
        )
        nodes.append(taglib_node)
        
        # Extract custom tags (closures at class body level)
        for method in cls.get("methods", []):
            tag_name = method.get("name", "")
            tag_line = method.get("line", 0)
            tag_end_line = method.get("endLine", tag_line + 1)
            
            custom_tag_props = {
                "namespace": namespace,
                "tag_name": tag_name,
                "has_body": True,
                "attrs": [p.get("name") for p in method.get("params", [])],
            }
            
            tag_node = Node(
                id=f"{project_id}:custom_tag:{namespace}:{tag_name}",
                kind="custom_tag",
                name=tag_name,
                fqn=f"{namespace}:{tag_name}",
                file_path=file_path,
                line_start=tag_line,
                line_end=tag_end_line,
                language="groovy",
                project_id=project_id,
                last_run_id=last_run_id,
                docstring=method.get("docstring"),
                source_hash="",
                properties=custom_tag_props,
                grails_version=None,
            )
            nodes.append(tag_node)
            
            edges.append(RawEdge(
                source_id=taglib_node.id,
                target_id=tag_node.id,
                target_hint="",
                type="DEFINES_TAG",
                file_path=file_path,
                line=tag_line,
                confidence="EXACT",
                extractor="taglib_extractor",
            ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
