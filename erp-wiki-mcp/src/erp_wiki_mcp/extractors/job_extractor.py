"""Job extractor for Grails jobs."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_job(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract job-specific nodes and edges."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        class_name = cls.get("name", "")
        class_line = cls.get("line", 0)
        class_end_line = cls.get("endLine", class_line + 1)
        
        # Extract triggers
        triggers = {}
        for field in cls.get("fields", []):
            if field.get("name") == "triggers":
                triggers = field.get("value", {})
        
        job_props = {
            "is_job": True,
            "triggers": triggers,
        }
        
        job_node = Node(
            id=f"{project_id}:job:{class_fqn}",
            kind="job",
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
            properties=job_props,
            grails_version=None,
        )
        nodes.append(job_node)
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
