"""Service extractor for Grails services."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_service(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """
    Extract service-specific nodes and edges.
    
    - Stamp class as service kind
    - Set transactional flag
    - Calculate bean_name from convention
    """
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        class_name = cls.get("name", "")
        class_line = cls.get("line", 0)
        class_end_line = cls.get("endLine", class_line + 1)
        
        # Determine transactional
        transactional = False
        annotations = cls.get("annotations", [])
        for ann in annotations:
            if ann.get("name") == "Transactional":
                transactional = True
                break
        
        # Check static transactional property
        for field in cls.get("fields", []):
            if field.get("name") == "transactional" and field.get("value") is True:
                transactional = True
        
        # Bean name: camelCase of class name (LoanService -> loanService)
        bean_name = class_name
        if bean_name.endswith("Service"):
            bean_name = bean_name[:-7]
        if bean_name:
            bean_name = bean_name[0].lower() + bean_name[1:]
        bean_name = f"{bean_name}Service"
        
        service_props = {
            "is_service": True,
            "transactional": transactional,
            "bean_name": bean_name,
        }
        
        service_node = Node(
            id=f"{project_id}:service:{class_fqn}",
            kind="service",
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
            properties=service_props,
            grails_version=None,
        )
        nodes.append(service_node)
        
        # Process methods
        for method in cls.get("methods", []):
            method_name = method.get("name", "")
            method_line = method.get("line", 0)
            method_end_line = method.get("endLine", method_line + 1)
            
            method_props = {
                "return_type": method.get("returnType", "def"),
                "params": [p.get("name") for p in method.get("params", [])],
                "is_transactional": transactional,
            }
            
            method_node = Node(
                id=f"{project_id}:method:{class_fqn}#{method_name}",
                kind="method",
                name=method_name,
                fqn=f"{class_fqn}#{method_name}",
                file_path=file_path,
                line_start=method_line,
                line_end=method_end_line,
                language="groovy",
                project_id=project_id,
                last_run_id=last_run_id,
                docstring=method.get("docstring"),
                source_hash="",
                properties=method_props,
                grails_version=None,
            )
            nodes.append(method_node)
            
            edges.append(RawEdge(
                source_id=service_node.id,
                target_id=method_node.id,
                target_hint="",
                type="DECLARES",
                file_path=file_path,
                line=method_line,
                confidence="EXACT",
                extractor="service_extractor",
            ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
