"""Domain extractor for Grails domain classes."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_domain(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract domain-specific nodes and edges including GORM DSL."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        class_name = cls.get("name", "")
        class_line = cls.get("line", 0)
        class_end_line = cls.get("endLine", class_line + 1)
        
        domain_props = {
            "is_domain": True,
            "has_many": {},
            "belongs_to": {},
            "has_one": {},
            "constraints": {},
            "table_name": None,
        }
        
        # Extract GORM DSL properties
        for field in cls.get("fields", []):
            fname = field.get("name", "")
            fvalue = field.get("value", {})
            
            if fname == "hasMany":
                domain_props["has_many"] = fvalue if isinstance(fvalue, dict) else {}
                for rel_name, rel_type in fvalue.items():
                    edges.append(RawEdge(
                        source_id=f"{project_id}:domain:{class_fqn}",
                        target_id="",
                        target_hint=f"domain:{rel_type}",
                        type="HAS_RELATION",
                        file_path=file_path,
                        line=field.get("line", class_line),
                        confidence="UNRESOLVED",
                        extractor="domain_extractor",
                    ))
            
            elif fname == "belongsTo":
                domain_props["belongs_to"] = fvalue if isinstance(fvalue, dict) else {}
                for rel_name, rel_type in fvalue.items():
                    edges.append(RawEdge(
                        source_id=f"{project_id}:domain:{class_fqn}",
                        target_id="",
                        target_hint=f"domain:{rel_type}",
                        type="HAS_RELATION",
                        file_path=file_path,
                        line=field.get("line", class_line),
                        confidence="UNRESOLVED",
                        extractor="domain_extractor",
                    ))
            
            elif fname == "hasOne":
                domain_props["has_one"] = fvalue if isinstance(fvalue, dict) else {}
        
        domain_node = Node(
            id=f"{project_id}:domain:{class_fqn}",
            kind="domain",
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
            properties=domain_props,
            grails_version=None,
        )
        nodes.append(domain_node)
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
