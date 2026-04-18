"""Java symbol and edge extractor using tree-sitter."""

import logging
from pathlib import Path

from tree_sitter import Node as TSNode

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.parsers.base import ParseResult
from erp_wiki_mcp.registry.models import Node, RawEdge

logger = logging.getLogger(__name__)

# DI annotations that indicate injection points
DI_ANNOTATIONS = {"@Autowired", "@Inject", "@Resource", "@Value", "@Qualifier"}

# Type suffixes that suggest DI candidates in Spring-style untyped Java
DI_TYPE_SUFFIXES = ("Service", "Repository", "Dao", "Manager", "Component", "Controller", "Factory")


def _get_javadoc_comment(node: TSNode, source: bytes) -> str | None:
    """Extract Javadoc comment immediately preceding a node."""
    prev_sibling = node.prev_sibling
    if prev_sibling is None:
        return None

    if prev_sibling.type == "block_comment":
        text = prev_sibling.text.decode("utf-8", errors="ignore")
        if text.startswith("/**"):
            # Strip /** and */
            docstring = text[3:-2].strip()
            # Remove leading * from each line
            lines = []
            for line in docstring.split("\n"):
                stripped = line.strip().lstrip("*").strip()
                if stripped:
                    lines.append(stripped)
            return "\n".join(lines)
    return None


def _get_annotations(node: TSNode) -> list[str]:
    """Extract annotations from a node's markers."""
    annotations = []
    for child in node.children:
        if child.type == "marker_annotation" or child.type == "annotation":
            ann_text = child.text.decode("utf-8", errors="ignore")
            annotations.append(ann_text)
    return annotations


def _has_di_annotation(annotations: list[str]) -> bool:
    """Check if any annotation indicates DI."""
    for ann in annotations:
        for di_ann in DI_ANNOTATIONS:
            if ann.startswith(di_ann):
                return True
    return False


def _is_di_candidate_type(type_name: str) -> bool:
    """Check if type name suggests a DI candidate."""
    for suffix in DI_TYPE_SUFFIXES:
        if type_name.endswith(suffix):
            return True
    return False


def _extract_package(source: bytes, root: TSNode) -> str:
    """Extract package name from source."""
    for child in root.children:
        if child.type == "package_declaration":
            # Find the identifier
            for grandchild in child.children:
                if grandchild.type == "identifier":
                    return grandchild.text.decode("utf-8", errors="ignore")
                elif grandchild.type == "scoped_identifier":
                    return grandchild.text.decode("utf-8", errors="ignore")
    return ""


def _collect_imports(root: TSNode) -> list[str]:
    """Collect all import declarations."""
    imports = []
    for child in root.children:
        if child.type == "import_declaration":
            # Extract the imported name
            for grandchild in child.children:
                if grandchild.type == "identifier":
                    imports.append(grandchild.text.decode("utf-8", errors="ignore"))
                elif grandchild.type == "scoped_identifier":
                    imports.append(grandchild.text.decode("utf-8", errors="ignore"))
                elif grandchild.type == "asterisk":
                    # Wildcard import - keep track of it
                    prefix_parts = []
                    for ggchild in grandchild.children:
                        if ggchild.type in ("identifier", "scoped_identifier"):
                            prefix_parts.append(ggchild.text.decode("utf-8", errors="ignore"))
                    if prefix_parts:
                        imports.append(".".join(prefix_parts) + ".*")
    return imports


def _get_fqn(package: str, class_name: str) -> str:
    """Build fully qualified name."""
    if package:
        return f"{package}.{class_name}"
    return class_name


def _get_method_signature(node: TSNode) -> str:
    """Extract method signature (param types)."""
    params = []
    for child in node.children:
        if child.type == "formal_parameters":
            for param in child.children:
                if param.type == "formal_parameter":
                    type_str = ""
                    for pchild in param.children:
                        if pchild.type in ("type_identifier", "scoped_identifier", "integral_type", "floating_point_type"):
                            type_str = pchild.text.decode("utf-8", errors="ignore")
                            break
                    if type_str:
                        params.append(type_str)
    return ",".join(params)


def _get_visibility(node: TSNode) -> str:
    """Extract visibility modifier."""
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                mod_text = mod.text.decode("utf-8", errors="ignore")
                if mod_text in ("public", "private", "protected"):
                    return mod_text
    return "package-private"


def _extract_class_nodes_and_edges(
    node: TSNode,
    package: str,
    file_path: str,
    source: bytes,
    imports: list[str],
) -> tuple[list[Node], list[RawEdge]]:
    """Extract nodes and edges from a class declaration."""
    nodes = []
    edges = []

    class_name = ""
    for child in node.children:
        if child.type == "identifier":
            class_name = child.text.decode("utf-8", errors="ignore")
            break

    if not class_name:
        return nodes, edges

    fqn = _get_fqn(package, class_name)
    line_start = node.start_point[0] + 1
    line_end = node.end_point[0] + 1
    docstring = _get_javadoc_comment(node, source)
    annotations = _get_annotations(node)

    # Determine class properties
    is_abstract = False
    is_interface = False
    is_enum = False
    superclass_hint = None
    interfaces_hints = []

    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                mod_text = mod.text.decode("utf-8", errors="ignore")
                if mod_text == "abstract":
                    is_abstract = True
        elif child.type == "superclass":
            for sc in child.children:
                if sc.type in ("type_identifier", "scoped_identifier"):
                    superclass_hint = sc.text.decode("utf-8", errors="ignore")
        elif child.type == "super_interfaces":
            for iface in child.children:
                if iface.type in ("type_list",):
                    for iface_child in iface.children:
                        if iface_child.type in ("type_identifier", "scoped_identifier"):
                            interfaces_hints.append(iface_child.text.decode("utf-8", errors="ignore"))

    class_node = Node(
        id=f"",  # Will be set by caller with project_id
        kind="class",
        name=class_name,
        fqn=fqn,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        language="java",
        project_id="",  # Will be set by caller
        last_run_id="",  # Will be set by caller
        docstring=docstring,
        properties={
            "is_abstract": is_abstract,
            "is_interface": is_interface,
            "is_enum": is_enum,
            "superclass_hint": superclass_hint,
            "interfaces_hints": interfaces_hints,
            "annotations": annotations,
        },
    )
    nodes.append(class_node)

    # Process children for methods, fields, etc.
    # Need to find class_body and iterate its children
    class_body = None
    for child in node.children:
        if child.type == "class_body":
            class_body = child
            break
    
    if class_body is not None:
        for child in class_body.children:
            if child.type == "method_declaration":
                method_nodes, method_edges = _extract_method_nodes_and_edges(
                    child, fqn, file_path, source, class_node.id
                )
                nodes.extend(method_nodes)
                edges.extend(method_edges)

                # Add DECLARES edge from class to method
                if method_nodes:
                    edges.append(
                        RawEdge(
                            source_id=class_node.id,
                            target_id=method_nodes[0].id,
                            target_hint=None,
                            type="DECLARES",
                            file_path=file_path,
                            line=child.start_point[0] + 1,
                            confidence="EXACT",
                            extractor="java",
                        )
                    )

            elif child.type == "constructor_declaration":
                ctor_nodes, ctor_edges = _extract_constructor_nodes_and_edges(
                    child, fqn, file_path, source, class_node.id
                )
                nodes.extend(ctor_nodes)
                edges.extend(ctor_edges)

                # Add DECLARES edge from class to constructor
                if ctor_nodes:
                    edges.append(
                        RawEdge(
                            source_id=class_node.id,
                            target_id=ctor_nodes[0].id,
                            target_hint=None,
                            type="DECLARES",
                            file_path=file_path,
                            line=child.start_point[0] + 1,
                            confidence="EXACT",
                            extractor="java",
                        )
                    )

            elif child.type == "field_declaration":
                field_nodes, field_edges = _extract_field_nodes_and_edges(
                    child, fqn, file_path, source, class_node.id
                )
                nodes.extend(field_nodes)
                edges.extend(field_edges)

                # Add DECLARES edge from class to field
                if field_nodes:
                    edges.append(
                        RawEdge(
                            source_id=class_node.id,
                            target_id=field_nodes[0].id,
                            target_hint=None,
                            type="DECLARES",
                            file_path=file_path,
                            line=child.start_point[0] + 1,
                            confidence="EXACT",
                            extractor="java",
                        )
                    )

    # Handle extends
    if superclass_hint:
        edges.append(
            RawEdge(
                source_id=class_node.id,
                target_id=None,
                target_hint=f"class:{superclass_hint}|file:{file_path}|imports:{','.join(imports)}",
                type="EXTENDS",
                file_path=file_path,
                line=line_start,
                confidence="UNRESOLVED",
                extractor="java",
            )
        )

    # Handle implements
    for iface_hint in interfaces_hints:
        edges.append(
            RawEdge(
                source_id=class_node.id,
                target_id=None,
                target_hint=f"interface:{iface_hint}|file:{file_path}|imports:{','.join(imports)}",
                type="IMPLEMENTS",
                file_path=file_path,
                line=line_start,
                confidence="UNRESOLVED",
                extractor="java",
            )
        )

    return nodes, edges


def _extract_method_nodes_and_edges(
    node: TSNode,
    class_fqn: str,
    file_path: str,
    source: bytes,
    class_id: str,
) -> tuple[list[Node], list[RawEdge]]:
    """Extract nodes and edges from a method declaration."""
    nodes = []
    edges = []

    method_name = ""
    return_type = ""
    is_static = False
    is_abstract = False
    visibility = "package-private"

    for child in node.children:
        if child.type == "identifier":
            method_name = child.text.decode("utf-8", errors="ignore")
        elif child.type == "type_identifier" or child.type == "void_type":
            return_type = child.text.decode("utf-8", errors="ignore")
        elif child.type == "modifiers":
            for mod in child.children:
                mod_text = mod.text.decode("utf-8", errors="ignore")
                if mod_text == "static":
                    is_static = True
                elif mod_text == "abstract":
                    is_abstract = True
                elif mod_text in ("public", "private", "protected"):
                    visibility = mod_text

    if not method_name:
        return nodes, edges

    param_types = _get_method_signature(node)
    fqn = f"{class_fqn}#{method_name}({param_types})"
    line_start = node.start_point[0] + 1
    line_end = node.end_point[0] + 1
    docstring = _get_javadoc_comment(node, source)
    annotations = _get_annotations(node)

    method_node = Node(
        id="",  # Will be set by caller
        kind="method",
        name=method_name,
        fqn=fqn,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        language="java",
        project_id="",
        last_run_id="",
        docstring=docstring,
        properties={
            "return_type_hint": return_type,
            "param_types": param_types,
            "is_static": is_static,
            "is_abstract": is_abstract,
            "visibility": visibility,
            "annotations": annotations,
        },
    )
    nodes.append(method_node)

    # Look for method invocations within the method body
    for child in node.children:
        if child.type == "block":
            call_edges = _extract_method_calls(child, file_path, source)
            edges.extend(call_edges)

    # Add ANNOTATED_WITH edges for annotations
    for ann in annotations:
        edges.append(
            RawEdge(
                source_id=method_node.id,
                target_id=None,
                target_hint=f"annotation:{ann}",
                type="ANNOTATED_WITH",
                file_path=file_path,
                line=line_start,
                confidence="UNRESOLVED",
                extractor="java",
            )
        )

    return nodes, edges


def _extract_constructor_nodes_and_edges(
    node: TSNode,
    class_fqn: str,
    file_path: str,
    source: bytes,
    class_id: str,
) -> tuple[list[Node], list[RawEdge]]:
    """Extract nodes and edges from a constructor declaration."""
    nodes = []
    edges = []

    constructor_name = ""
    param_types = ""
    visibility = "package-private"

    for child in node.children:
        if child.type == "identifier":
            constructor_name = child.text.decode("utf-8", errors="ignore")
        elif child.type == "formal_parameters":
            param_types = _get_method_signature(node)
        elif child.type == "modifiers":
            for mod in child.children:
                mod_text = mod.text.decode("utf-8", errors="ignore")
                if mod_text in ("public", "private", "protected"):
                    visibility = mod_text

    if not constructor_name:
        return nodes, edges

    fqn = f"{class_fqn}#{constructor_name}({param_types})"
    line_start = node.start_point[0] + 1
    line_end = node.end_point[0] + 1
    docstring = _get_javadoc_comment(node, source)

    constructor_node = Node(
        id="",
        kind="constructor",
        name=constructor_name,
        fqn=fqn,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        language="java",
        project_id="",
        last_run_id="",
        docstring=docstring,
        properties={
            "param_types": param_types,
            "visibility": visibility,
        },
    )
    nodes.append(constructor_node)

    return nodes, edges


def _extract_field_nodes_and_edges(
    node: TSNode,
    class_fqn: str,
    file_path: str,
    source: bytes,
    class_id: str,
) -> tuple[list[Node], list[RawEdge]]:
    """Extract nodes and edges from a field declaration."""
    nodes = []
    edges = []

    field_name = ""
    field_type = ""
    is_static = False
    is_final = False
    visibility = "package-private"
    annotations = _get_annotations(node)

    is_di_candidate = _has_di_annotation(annotations)
    injection_point = is_di_candidate
    qualifier_hint = None

    # Extract qualifier from @Qualifier or @Resource
    for ann in annotations:
        if "@Qualifier" in ann or "@Resource" in ann:
            # Try to extract the name value
            if 'name=' in ann or 'value=' in ann:
                # Simple extraction - look for quoted string
                import re
                match = re.search(r'(?:name|value)\s*=\s*"([^"]+)"', ann)
                if match:
                    qualifier_hint = match.group(1)

    for child in node.children:
        if child.type == "variable_declarator":
            for vchild in child.children:
                if vchild.type == "identifier":
                    field_name = vchild.text.decode("utf-8", errors="ignore")
        elif child.type == "type_identifier" or child.type == "scoped_identifier":
            field_type = child.text.decode("utf-8", errors="ignore")
        elif child.type == "modifiers":
            for mod in child.children:
                mod_text = mod.text.decode("utf-8", errors="ignore")
                if mod_text == "static":
                    is_static = True
                elif mod_text == "final":
                    is_final = True
                elif mod_text in ("public", "private", "protected"):
                    visibility = mod_text

    if not field_name:
        return nodes, edges

    # Check if type suggests DI candidate (Spring-style untyped Java)
    if field_type and _is_di_candidate_type(field_type):
        is_di_candidate = True
        injection_point = True

    fqn = f"{class_fqn}#{field_name}"
    line_start = node.start_point[0] + 1
    line_end = node.end_point[0] + 1
    docstring = _get_javadoc_comment(node, source)

    field_node = Node(
        id="",
        kind="field",
        name=field_name,
        fqn=fqn,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        language="java",
        project_id="",
        last_run_id="",
        docstring=docstring,
        properties={
            "type_hint": field_type,
            "is_static": is_static,
            "is_final": is_final,
            "is_di_candidate": is_di_candidate,
            "injection_point": injection_point,
            "visibility": visibility,
            "annotations": annotations,
            "qualifier_hint": qualifier_hint,
        },
    )
    nodes.append(field_node)

    # Add INJECTS edge for DI fields
    if is_di_candidate and field_type:
        edges.append(
            RawEdge(
                source_id=field_node.id,
                target_id=None,
                target_hint=f"service:{field_name}|class:{class_fqn}|file:{file_path}",
                type="INJECTS",
                file_path=file_path,
                line=line_start,
                confidence="UNRESOLVED",
                extractor="java",
            )
        )

    # Add USES_TYPE edge
    if field_type:
        edges.append(
            RawEdge(
                source_id=field_node.id,
                target_id=None,
                target_hint=f"type:{field_type}",
                type="USES_TYPE",
                file_path=file_path,
                line=line_start,
                confidence="UNRESOLVED",
                extractor="java",
            )
        )

    # Add ANNOTATED_WITH edges
    for ann in annotations:
        edges.append(
            RawEdge(
                source_id=field_node.id,
                target_id=None,
                target_hint=f"annotation:{ann}",
                type="ANNOTATED_WITH",
                file_path=file_path,
                line=line_start,
                confidence="UNRESOLVED",
                extractor="java",
            )
        )

    return nodes, edges


def _extract_method_calls(node: TSNode, file_path: str, source: bytes) -> list[RawEdge]:
    """Extract method invocation edges from a block."""
    edges = []

    for child in node.children:
        if child.type == "method_invocation":
            method_name = ""
            receiver = ""

            for cchild in child.children:
                if cchild.type == "identifier":
                    method_name = cchild.text.decode("utf-8", errors="ignore")
                elif cchild.type == "member_expression":
                    # this.foo() or obj.foo()
                    for mchild in cchild.children:
                        if mchild.type == "identifier":
                            receiver = mchild.text.decode("utf-8", errors="ignore")

            if method_name:
                edges.append(
                    RawEdge(
                        source_id="",  # Will be filled by caller
                        target_id=None,
                        target_hint=f"method:{method_name}|receiver:{receiver}|file:{file_path}",
                        type="CALLS",
                        file_path=file_path,
                        line=child.start_point[0] + 1,
                        confidence="UNRESOLVED",
                        extractor="java",
                    )
                )

        elif child.type == "object_creation_expression":
            # new Foo()
            type_name = ""
            for cchild in child.children:
                if cchild.type in ("type_identifier", "scoped_identifier"):
                    type_name = cchild.text.decode("utf-8", errors="ignore")
                    break

            if type_name:
                edges.append(
                    RawEdge(
                        source_id="",
                        target_id=None,
                        target_hint=f"class:{type_name}|file:{file_path}",
                        type="INSTANTIATES",
                        file_path=file_path,
                        line=child.start_point[0] + 1,
                        confidence="UNRESOLVED",
                        extractor="java",
                    )
                )

        # Recurse into nested blocks
        elif child.type == "block":
            edges.extend(_extract_method_calls(child, file_path, source))

        elif child.type == "if_statement":
            for cchild in child.children:
                if cchild.type == "block":
                    edges.extend(_extract_method_calls(cchild, file_path, source))

        elif child.type == "for_statement" or child.type == "while_statement":
            for cchild in child.children:
                if cchild.type == "block":
                    edges.extend(_extract_method_calls(cchild, file_path, source))

    return edges


def extract_java(parse_result: ParseResult, project_id: str, run_id: str) -> ExtractorResult:
    """
    Extract symbols and edges from a parsed Java file.

    Args:
        parse_result: Result from java_parser
        project_id: Project identifier for node IDs
        run_id: Current run identifier

    Returns:
        ExtractorResult with nodes and raw edges
    """
    nodes = []
    edges = []

    if parse_result.tree is None:
        return ExtractorResult(nodes=[], raw_edges=[])

    tree = parse_result.tree
    root = tree.root_node
    source = parse_result.raw_source

    # Extract package and imports
    package = _extract_package(source, root)
    imports = _collect_imports(root)

    # Walk the tree for top-level declarations
    for child in root.children:
        if child.type == "class_declaration":
            class_nodes, class_edges = _extract_class_nodes_and_edges(
                child, package, parse_result.file_path, source, imports
            )
            nodes.extend(class_nodes)
            edges.extend(class_edges)

        elif child.type == "interface_declaration":
            # Similar to class but mark as interface
            interface_nodes, interface_edges = _extract_class_nodes_and_edges(
                child, package, parse_result.file_path, source, imports
            )
            for n in interface_nodes:
                n.kind = "interface"
                n.properties["is_interface"] = True
            nodes.extend(interface_nodes)
            edges.extend(interface_edges)

        elif child.type == "enum_declaration":
            enum_nodes, enum_edges = _extract_class_nodes_and_edges(
                child, package, parse_result.file_path, source, imports
            )
            for n in enum_nodes:
                n.kind = "enum"
                n.properties["is_enum"] = True
            nodes.extend(enum_nodes)
            edges.extend(enum_edges)

    # Generate unique IDs for all nodes FIRST, before creating edges
    # Format: {project_id}:{kind}:{fqn_or_path}[#{member}][({signature})]
    for node in nodes:
        node.project_id = project_id
        node.last_run_id = run_id
        # Create ID from project_id, kind, and fqn
        node.id = f"{project_id}:{node.kind}:{node.fqn}"

    return ExtractorResult(nodes=nodes, raw_edges=edges)
