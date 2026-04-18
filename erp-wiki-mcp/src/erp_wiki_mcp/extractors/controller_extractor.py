"""Controller extractor for Grails controllers."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_controller(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """
    Extract controller-specific nodes and edges.
    
    Extends groovy_extractor output with:
    - Stamp class node as controller kind
    - Convert methods/closures to action nodes
    - Extract allowedMethods
    - Detect render/redirect/forward/chain calls
    - Detect params access
    - Detect domain queries
    """
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    # Process each class in the AST
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        class_name = cls.get("name", "")
        class_line = cls.get("line", 0)
        class_end_line = cls.get("endLine", class_line + 1)
        
        # Create controller node
        controller_props = {
            "is_controller": True,
            "allowed_methods": {},
            "transactional": cls.get("transactional", False),
        }
        
        # Extract allowedMethods static map
        for field in cls.get("fields", []):
            if field.get("name") == "allowedMethods":
                controller_props["allowed_methods"] = field.get("value", {})
        
        controller_node = Node(
            id=f"{project_id}:controller:{class_fqn}",
            kind="controller",
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
            properties=controller_props,
            grails_version=None,
        )
        nodes.append(controller_node)
        
        # Process methods as actions
        for method in cls.get("methods", []):
            method_name = method.get("name", "")
            
            # Skip internal methods (starting with _)
            if method_name.startswith("_"):
                continue
            
            method_line = method.get("line", 0)
            method_end_line = method.get("endLine", method_line + 1)
            
            # Create action node
            action_props = {
                "controller_id": controller_node.id,
                "http_methods": [],
                "is_closure_style": method.get("is_closure", False),
                "response_formats": [],
                "renders_view": None,
                "return_type": method.get("returnType", "def"),
                "params": [p.get("name") for p in method.get("params", [])],
            }
            
            action_node = Node(
                id=f"{project_id}:action:{class_fqn}#{method_name}",
                kind="action",
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
                properties=action_props,
                grails_version=None,
            )
            nodes.append(action_node)
            
            # DECLARES edge from controller to action
            edges.append(RawEdge(
                source_id=controller_node.id,
                target_id=action_node.id,
                target_hint="",
                type="DECLARES",
                file_path=file_path,
                line=method_line,
                confidence="EXACT",
                extractor="controller_extractor",
            ))
            
            # Analyze method body for render/redirect/forward/chain calls
            body = method.get("body", {})
            _analyze_action_body(
                body, action_node, file_path, project_id, 
                last_run_id, edges, class_fqn
            )
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)


def _analyze_action_body(body: dict, action_node: Node, file_path: str, 
                         project_id: str, last_run_id: str, 
                         edges: list[RawEdge], controller_fqn: str) -> None:
    """Analyze action body for Grails-specific patterns."""
    statements = body.get("statements", []) if isinstance(body, dict) else []
    
    for stmt in statements:
        stmt_type = stmt.get("type", "")
        line = stmt.get("line", action_node.line_start)
        
        # Detect render() calls
        if stmt_type == "render_call":
            view = stmt.get("view")
            if view:
                action_node.properties["renders_view"] = view
                edges.append(RawEdge(
                    source_id=action_node.id,
                    target_id="",
                    target_hint=f"view:{view}",
                    type="RENDERS",
                    file_path=file_path,
                    line=line,
                    confidence="UNRESOLVED",
                    extractor="controller_extractor",
                ))
            
            # Check for JSON response
            if stmt.get("as_json") or stmt.get("format") == "json":
                action_node.properties["response_formats"].append("json")
                edges.append(RawEdge(
                    source_id=action_node.id,
                    target_id="",
                    target_hint="format:json",
                    type="RETURNS_FORMAT",
                    file_path=file_path,
                    line=line,
                    confidence="EXACT",
                    extractor="controller_extractor",
                ))
            
            # Check status codes
            status = stmt.get("status")
            if status:
                edges.append(RawEdge(
                    source_id=action_node.id,
                    target_id="",
                    target_hint=f"status:{status}",
                    type="RETURNS_STATUS",
                    file_path=file_path,
                    line=line,
                    confidence="EXACT",
                    extractor="controller_extractor",
                ))
        
        # Detect redirect() calls
        elif stmt_type == "redirect_call":
            action = stmt.get("action")
            controller = stmt.get("controller")
            uri = stmt.get("uri")
            
            hint = f"action:{action}"
            if controller:
                hint += f",controller:{controller}"
            if uri:
                hint = f"uri:{uri}"
            
            edges.append(RawEdge(
                source_id=action_node.id,
                target_id="",
                target_hint=hint,
                type="REDIRECTS_TO",
                file_path=file_path,
                line=line,
                confidence="UNRESOLVED",
                extractor="controller_extractor",
            ))
        
        # Detect forward() calls
        elif stmt_type == "forward_call":
            action = stmt.get("action")
            edges.append(RawEdge(
                source_id=action_node.id,
                target_id="",
                target_hint=f"action:{action}",
                type="FORWARDS_TO",
                file_path=file_path,
                line=line,
                confidence="UNRESOLVED",
                extractor="controller_extractor",
            ))
        
        # Detect chain() calls
        elif stmt_type == "chain_call":
            action = stmt.get("action")
            edges.append(RawEdge(
                source_id=action_node.id,
                target_id="",
                target_hint=f"action:{action}",
                type="CHAINS_TO",
                file_path=file_path,
                line=line,
                confidence="UNRESOLVED",
                extractor="controller_extractor",
            ))
        
        # Detect params.x access
        elif stmt_type == "params_access":
            param_name = stmt.get("param_name")
            if param_name:
                query_param_node = Node(
                    id=f"{project_id}:query_param:{action_node.fqn}#{param_name}",
                    kind="query_param",
                    name=param_name,
                    fqn=f"{action_node.fqn}#{param_name}",
                    file_path=file_path,
                    line_start=line,
                    line_end=line,
                    language="groovy",
                    project_id=project_id,
                    last_run_id=last_run_id,
                    docstring=None,
                    source_hash="",
                    properties={"action_id": action_node.id},
                    grails_version=None,
                )
                edges.append(RawEdge(
                    source_id=action_node.id,
                    target_id=query_param_node.id,
                    target_hint="",
                    type="ACCEPTS_PARAM",
                    file_path=file_path,
                    line=line,
                    confidence="EXACT",
                    extractor="controller_extractor",
                ))
        
        # Detect domain queries (Loan.findByX, Loan.get)
        elif stmt_type == "domain_query":
            domain_class = stmt.get("domain_class")
            method = stmt.get("method")
            edges.append(RawEdge(
                source_id=action_node.id,
                target_id="",
                target_hint=f"domain:{domain_class}",
                type="QUERIES_DOMAIN",
                file_path=file_path,
                line=line,
                confidence="UNRESOLVED",
                extractor="controller_extractor",
            ))
        
        # Detect command object binding
        elif stmt_type == "command_binding":
            command_class = stmt.get("command_class")
            param_name = stmt.get("param_name")
            edges.append(RawEdge(
                source_id=action_node.id,
                target_id="",
                target_hint=f"command:{command_class}",
                type="BINDS_COMMAND",
                file_path=file_path,
                line=line,
                confidence="UNRESOLVED",
                extractor="controller_extractor",
            ))
