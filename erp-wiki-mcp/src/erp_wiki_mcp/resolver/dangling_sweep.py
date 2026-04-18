"""Dangling edge sweep (Pass 4)."""

from dataclasses import dataclass, field


@dataclass
class DanglingSweepResult:
    """Result of dangling edge sweep."""

    deleted_edge_ids: list[str] = field(default_factory=list)
    downgraded_edges: list = field(default_factory=list)  # edges downgraded to UNRESOLVED
    warnings: list = field(default_factory=list)


def run_dangling_sweep(
    edges: list,
    existing_node_ids: set[str],
    deleted_file_paths: set[str],
) -> DanglingSweepResult:
    """
    Run dangling edge sweep.

    For every edge in graph:
    - Source missing (deleted this run) → delete edge entirely
    - Target missing AND previously EXACT → downgrade to UNRESOLVED, emit warning
    - Target missing AND was UNRESOLVED → keep as-is

    Args:
        edges: List of edges to check
        existing_node_ids: Set of all existing node IDs in the graph
        deleted_file_paths: Set of file paths that were deleted this run

    Returns:
        DanglingSweepResult with actions to take
    """
    result = DanglingSweepResult()

    for edge in edges:
        source_id = getattr(edge, "source_id", None)
        target_id = getattr(edge, "target_id", None)
        confidence = getattr(edge, "confidence", "UNRESOLVED")
        file_path = getattr(edge, "file_path", "")
        line = getattr(edge, "line", 0)
        edge_type = getattr(edge, "type", "")

        # Check if source is from a deleted file
        if file_path in deleted_file_paths:
            # Source is from deleted file - mark for deletion
            if hasattr(edge, "id"):
                result.deleted_edge_ids.append(edge.id)
            continue

        # Check if source node exists
        if source_id and source_id not in existing_node_ids:
            # Source is missing - delete edge
            if hasattr(edge, "id"):
                result.deleted_edge_ids.append(edge.id)
            continue

        # Check if target exists (if it was resolved)
        if target_id and target_id not in existing_node_ids:
            if confidence == "EXACT":
                # Previously exact but now missing - downgrade
                edge.confidence = "UNRESOLVED"
                edge.target_id = None
                result.downgraded_edges.append(edge)

                # Emit appropriate warning based on edge type
                warning_code = _get_warning_code(edge_type, edge)
                if warning_code:
                    result.warnings.append({
                        "code": warning_code,
                        "edge_type": edge_type,
                        "source_id": source_id,
                        "hint": getattr(edge, "target_hint", ""),
                        "file_path": file_path,
                        "line": line,
                    })
            # If already UNRESOLVED, keep as-is

    return result


def _get_warning_code(edge_type: str, edge) -> str | None:
    """Get appropriate warning code for edge type."""
    if edge_type == "CALLS":
        return "ambiguous_call"
    elif edge_type == "INJECTS":
        return "unresolved_di"
    elif edge_type in ("EXTENDS", "IMPLEMENTS", "USES_TYPE"):
        return "missing_symbol"
    return None
