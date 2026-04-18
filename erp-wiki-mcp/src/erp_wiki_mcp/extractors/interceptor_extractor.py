"""Interceptor extractor for Grails 3.x interceptors."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_interceptor(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract Grails 3.x interceptor definitions."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        class_name = cls.get("name", "")
        class_line = cls.get("line", 0)
        
        interceptor_props = {
            "is_interceptor": True,
            "match_patterns": [],
        }
        
        interceptor_node = Node(
            id=f"{project_id}:interceptor:{class_fqn}",
            kind="interceptor",
            name=class_name,
            fqn=class_fqn,
            file_path=file_path,
            line_start=class_line,
            line_end=class_line + 1,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=cls.get("docstring"),
            source_hash="",
            properties=interceptor_props,
            grails_version="3.x",
        )
        nodes.append(interceptor_node)
        
        # Extract match() calls
        matches = cls.get("matches", [])
        for match in matches:
            controller = match.get("controller", "")
            action = match.get("action", "")
            is_match_all = match.get("match_all", False)
            
            target_hint = ""
            confidence = "UNRESOLVED"
            
            if is_match_all:
                target_hint = "all"
                confidence = "HEURISTIC"
            elif controller:
                target_hint = f"controller:{controller}"
                if action:
                    target_hint += f",action:{action}"
                confidence = "LIKELY"
            
            edges.append(RawEdge(
                source_id=interceptor_node.id,
                target_id="",
                target_hint=target_hint,
                type="APPLIES_TO",
                file_path=file_path,
                line=match.get("line", class_line),
                confidence=confidence,
                extractor="interceptor_extractor",
            ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
