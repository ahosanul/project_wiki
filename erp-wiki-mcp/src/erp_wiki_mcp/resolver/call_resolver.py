"""Resolver for method calls and other unresolved edges."""

from dataclasses import dataclass, field


@dataclass
class ResolvedEdge:
    """An edge that has been resolved."""

    source_id: str
    target_id: str
    type: str
    file_path: str
    line: int
    confidence: str  # EXACT | LIKELY | HEURISTIC
    extractor: str


@dataclass
class ResolverWarning:
    """A warning from the resolver."""

    code: str  # missing_view | missing_template | unresolved_di | ambiguous_call
    edge_type: str
    source_id: str
    hint: str
    file_path: str
    line: int


@dataclass
class ResolverResult:
    """Result of resolution pass."""

    resolved: list[ResolvedEdge] = field(default_factory=list)
    unresolved: list = field(default_factory=list)  # RawEdge
    warnings: list[ResolverWarning] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # edge IDs removed


def resolve_calls(
    raw_edges: list,
    index_tables,
    nodes_by_id: dict[str, any],
    file_to_nodes: dict[str, list],
) -> ResolverResult:
    """
    Resolve CALLS, INSTANTIATES, USES_TYPE edges (Pass 2).

    Args:
        raw_edges: List of RawEdge objects with UNRESOLVED confidence
        index_tables: IndexTables from index_builder
        nodes_by_id: Map of node ID to Node object
        file_to_nodes: Map of file_path to list of nodes in that file

    Returns:
        ResolverResult with resolved and unresolved edges
    """
    result = ResolverResult()

    for edge in raw_edges:
        if edge.type not in ("CALLS", "INSTANTIATES", "USES_TYPE", "THROWS"):
            result.unresolved.append(edge)
            continue

        if edge.type == "CALLS":
            resolved = _resolve_call(edge, index_tables, nodes_by_id, file_to_nodes)
            if resolved:
                result.resolved.append(resolved)
            else:
                result.unresolved.append(edge)

        elif edge.type == "INSTANTIATES":
            resolved = _resolve_instantiation(edge, index_tables)
            if resolved:
                result.resolved.append(resolved)
            else:
                result.unresolved.append(edge)

        elif edge.type == "USES_TYPE":
            resolved = _resolve_uses_type(edge, index_tables)
            if resolved:
                result.resolved.append(resolved)
            else:
                result.unresolved.append(edge)

    return result


def _resolve_call(edge, index_tables, nodes_by_id, file_to_nodes) -> ResolvedEdge | None:
    """Resolve a CALLS edge."""
    target_hint = edge.target_hint or ""

    # Parse hint: method:{name}|receiver:{receiver_expr}|class:{enclosing}|file:{file_path}
    parts = {}
    for part in target_hint.split("|"):
        if ":" in part:
            key, value = part.split(":", 1)
            parts[key] = value

    method_name = parts.get("method", "")
    receiver = parts.get("receiver", "")

    # Resolution order:
    # 1. this.foo() or self call → walk enclosing class methods
    if receiver == "this" or receiver == "":
        # Find enclosing class for this source
        source_node = nodes_by_id.get(edge.source_id)
        if source_node:
            # Look for methods with same name in the same class
            file_nodes = file_to_nodes.get(source_node.file_path, [])
            for node in file_nodes:
                if node.kind == "method" and node.name == method_name:
                    # Check if it's in the same class (fqn prefix matches)
                    source_class = source_node.fqn.rsplit("#", 1)[0]
                    target_class = node.fqn.rsplit("#", 1)[0]
                    if source_class == target_class:
                        return ResolvedEdge(
                            source_id=edge.source_id,
                            target_id=node.id,
                            type=edge.type,
                            file_path=edge.file_path,
                            line=edge.line,
                            confidence="EXACT",
                            extractor=edge.extractor,
                        )

    # 2. Receiver is DI field resolved in Pass 1 → look up method on that type
    if receiver and receiver in index_tables.bean_name_to_id:
        field_node_id = index_tables.bean_name_to_id[receiver]
        field_node = nodes_by_id.get(field_node_id)
        if field_node:
            type_hint = field_node.properties.get("type_hint", "")
            if type_hint:
                # Look for method on that type
                target_fqn = f"{type_hint}#{method_name}"
                if target_fqn in index_tables.fqn_to_id:
                    return ResolvedEdge(
                        source_id=edge.source_id,
                        target_id=index_tables.fqn_to_id[target_fqn],
                        type=edge.type,
                        file_path=edge.file_path,
                        line=edge.line,
                        confidence="LIKELY",
                        extractor=edge.extractor,
                    )

    # 3. Static Foo.bar() → imports → fqn_to_id
    if "." in method_name or receiver and receiver[0].isupper():
        # Could be static call
        class_name = receiver if receiver else method_name.split(".")[0]
        simple_method = method_name.split(".")[-1] if "." in method_name else method_name

        # Try to find via imports
        source_node = nodes_by_id.get(edge.source_id)
        if source_node:
            imports = index_tables.file_imports.get(source_node.file_path, [])
            for imp in imports:
                if imp.endswith(f".{class_name}") or imp == class_name:
                    target_fqn = f"{imp}#{simple_method}"
                    if target_fqn in index_tables.fqn_to_id:
                        return ResolvedEdge(
                            source_id=edge.source_id,
                            target_id=index_tables.fqn_to_id[target_fqn],
                            type=edge.type,
                            file_path=edge.file_path,
                            line=edge.line,
                            confidence="EXACT",
                            extractor=edge.extractor,
                        )

    # 4. Untyped receiver, method globally unique → HEURISTIC
    if method_name in index_tables.simple_name_to_ids:
        candidates = index_tables.simple_name_to_ids[method_name]
        if len(candidates) == 1:
            return ResolvedEdge(
                source_id=edge.source_id,
                target_id=candidates[0],
                type=edge.type,
                file_path=edge.file_path,
                line=edge.line,
                confidence="HEURISTIC",
                extractor=edge.extractor,
            )

    return None


def _resolve_instantiation(edge, index_tables) -> ResolvedEdge | None:
    """Resolve an INSTANTIATES edge."""
    target_hint = edge.target_hint or ""

    # Parse hint: class:{type_name}|file:{file_path}
    parts = {}
    for part in target_hint.split("|"):
        if ":" in part:
            key, value = part.split(":", 1)
            parts[key] = value

    class_name = parts.get("class", "")

    # Try direct FQN lookup
    if class_name in index_tables.fqn_to_id:
        return ResolvedEdge(
            source_id=edge.source_id,
            target_id=index_tables.fqn_to_id[class_name],
            type=edge.type,
            file_path=edge.file_path,
            line=edge.line,
            confidence="EXACT",
            extractor=edge.extractor,
        )

    # Try simple name lookup
    if class_name in index_tables.simple_name_to_ids:
        candidates = index_tables.simple_name_to_ids[class_name]
        if len(candidates) == 1:
            return ResolvedEdge(
                source_id=edge.source_id,
                target_id=candidates[0],
                type=edge.type,
                file_path=edge.file_path,
                line=edge.line,
                confidence="LIKELY",
                extractor=edge.extractor,
            )

    return None


def _resolve_uses_type(edge, index_tables) -> ResolvedEdge | None:
    """Resolve a USES_TYPE edge."""
    target_hint = edge.target_hint or ""

    # Parse hint: type:{type_name}
    parts = {}
    for part in target_hint.split("|"):
        if ":" in part:
            key, value = part.split(":", 1)
            parts[key] = value

    type_name = parts.get("type", "")

    # Try direct FQN lookup
    if type_name in index_tables.fqn_to_id:
        return ResolvedEdge(
            source_id=edge.source_id,
            target_id=index_tables.fqn_to_id[type_name],
            type=edge.type,
            file_path=edge.file_path,
            line=edge.line,
            confidence="EXACT",
            extractor=edge.extractor,
        )

    # Try simple name lookup
    if type_name in index_tables.simple_name_to_ids:
        candidates = index_tables.simple_name_to_ids[type_name]
        if len(candidates) == 1:
            return ResolvedEdge(
                source_id=edge.source_id,
                target_id=candidates[0],
                type=edge.type,
                file_path=edge.file_path,
                line=edge.line,
                confidence="LIKELY",
                extractor=edge.extractor,
            )

    return None
