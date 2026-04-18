"""Graph upsert operations with shadow-write strategy."""

import json
import logging

from erp_wiki_mcp.graph.store import GraphStore
from erp_wiki_mcp.registry.models import Node, RawEdge

logger = logging.getLogger(__name__)


def serialize_properties(props: dict) -> str:
    """Serialize node properties to JSON string."""
    return json.dumps(props) if props else "{}"


def upsert_nodes(
    store: GraphStore,
    nodes: list[Node],
    run_id: str,
    tx=None,
) -> tuple[int, int]:
    """
    UPSERT nodes using shadow-write strategy.

    Phase 1: Stage - UPSERT all new/updated Symbol nodes tagged with current_run_id.
    UPSERT logic: if EXISTS(id) → UPDATE where source_hash changed; else INSERT.

    Args:
        store: Graph store
        nodes: List of Node objects to upsert
        run_id: Current run ID
        tx: Optional transaction (if None, creates own transaction)

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    inserted = 0
    updated = 0

    should_commit = tx is None
    if should_commit:
        tx = store.begin_transaction()

    try:
        for node in nodes:
            # Check if node exists
            check_query = "MATCH (s:Symbol {id: $id}) RETURN s.id"
            result = store.execute(check_query, {"id": node.id})
            exists = result.has_next()

            if exists:
                # Update if source_hash changed
                update_query = """
                MATCH (s:Symbol {id: $id})
                SET s.name = $name,
                    s.fqn = $fqn,
                    s.file_path = $file_path,
                    s.line_start = $line_start,
                    s.line_end = $line_end,
                    s.language = $language,
                    s.project_id = $project_id,
                    s.last_run_id = $last_run_id,
                    s.docstring = $docstring,
                    s.source_hash = $source_hash,
                    s.properties = $properties,
                    s.kind = $kind
                """
                store.execute(
                    update_query,
                    {
                        "id": node.id,
                        "name": node.name,
                        "fqn": node.fqn,
                        "file_path": node.file_path,
                        "line_start": node.line_start,
                        "line_end": node.line_end,
                        "language": node.language,
                        "project_id": node.project_id,
                        "last_run_id": run_id,
                        "docstring": node.docstring or "",
                        "source_hash": node.source_hash or "",
                        "properties": serialize_properties(node.properties),
                        "kind": node.kind,
                    },
                )
                updated += 1
            else:
                # Insert new node
                insert_query = """
                CREATE (s:Symbol {
                    id: $id,
                    kind: $kind,
                    name: $name,
                    fqn: $fqn,
                    file_path: $file_path,
                    line_start: $line_start,
                    line_end: $line_end,
                    language: $language,
                    project_id: $project_id,
                    last_run_id: $last_run_id,
                    docstring: $docstring,
                    source_hash: $source_hash,
                    properties: $properties
                })
                """
                store.execute(
                    insert_query,
                    {
                        "id": node.id,
                        "kind": node.kind,
                        "name": node.name,
                        "fqn": node.fqn,
                        "file_path": node.file_path,
                        "line_start": node.line_start,
                        "line_end": node.line_end,
                        "language": node.language,
                        "project_id": node.project_id,
                        "last_run_id": run_id,
                        "docstring": node.docstring or "",
                        "source_hash": node.source_hash or "",
                        "properties": serialize_properties(node.properties),
                    },
                )
                inserted += 1

        if should_commit:
            tx.commit()

    except Exception as e:
        if should_commit:
            tx.rollback()
        logger.exception(f"Failed to upsert nodes: {e}")
        raise

    return inserted, updated


def upsert_edges(
    store: GraphStore,
    edges: list[RawEdge],
    run_id: str,
    tx=None,
) -> int:
    """
    UPSERT edges using shadow-write strategy.

    Args:
        store: Graph store
        edges: List of RawEdge objects to upsert
        run_id: Current run ID
        tx: Optional transaction

    Returns:
        Number of edges inserted/updated
    """
    count = 0

    should_commit = tx is None
    if should_commit:
        tx = store.begin_transaction()

    try:
        for edge in edges:
            # Only create edges where both source and target exist
            if not edge.source_id:
                continue

            # For unresolved edges (no target_id), we still store them with target_hint
            if edge.target_id:
                # Create relationship between existing nodes
                create_query = """
                MATCH (src:Symbol {id: $source_id})
                MATCH (tgt:Symbol {id: $target_id})
                CREATE (src)-[e:Edge {
                    type: $type,
                    confidence: $confidence,
                    file_path: $file_path,
                    line: $line,
                    extractor: $extractor,
                    target_hint: $target_hint,
                    last_run_id: $last_run_id,
                    extra: $extra
                }]->(tgt)
                """
                store.execute(
                    create_query,
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "type": edge.type,
                        "confidence": edge.confidence or "UNRESOLVED",
                        "file_path": edge.file_path,
                        "line": edge.line,
                        "extractor": edge.extractor,
                        "target_hint": edge.target_hint or "",
                        "last_run_id": run_id,
                        "extra": "",
                    },
                )
            else:
                # Unresolved edge - store with target_hint only
                create_query = """
                MATCH (src:Symbol {id: $source_id})
                CREATE (src)-[e:Edge {
                    type: $type,
                    confidence: $confidence,
                    file_path: $file_path,
                    line: $line,
                    extractor: $extractor,
                    target_hint: $target_hint,
                    last_run_id: $last_run_id,
                    extra: ""
                }]
                """
                store.execute(
                    create_query,
                    {
                        "source_id": edge.source_id,
                        "type": edge.type,
                        "confidence": edge.confidence or "UNRESOLVED",
                        "file_path": edge.file_path,
                        "line": edge.line,
                        "extractor": edge.extractor,
                        "target_hint": edge.target_hint or "",
                        "last_run_id": run_id,
                        "extra": "",
                    },
                )
            count += 1

        if should_commit:
            tx.commit()

    except Exception as e:
        if should_commit:
            tx.rollback()
        logger.exception(f"Failed to upsert edges: {e}")
        raise

    return count


def delete_stale_symbols(
    store: GraphStore,
    project_id: str,
    file_path: str,
    current_run_id: str,
    tx=None,
) -> int:
    """
    Delete stale symbols for a modified file.

    DELETE Symbol where project_id=X AND file_path=file AND last_run_id != current_run_id.
    Cascade: edges are automatically deleted due to foreign key constraints.

    Args:
        store: Graph store
        project_id: Project ID
        file_path: File path
        current_run_id: Current run ID

    Returns:
        Number of symbols deleted
    """
    should_commit = tx is None
    if should_commit:
        tx = store.begin_transaction()

    try:
        # First delete edges involving stale symbols
        delete_edges_query = """
        MATCH (s:Symbol {project_id: $project_id, file_path: $file_path})
        WHERE s.last_run_id <> $current_run_id
        MATCH ()-[e:Edge]-(s)
        DELETE e
        """
        store.execute(
            delete_edges_query,
            {
                "project_id": project_id,
                "file_path": file_path,
                "current_run_id": current_run_id,
            },
        )

        # Then delete the stale symbols
        delete_query = """
        MATCH (s:Symbol {project_id: $project_id, file_path: $file_path})
        WHERE s.last_run_id <> $current_run_id
        DELETE s
        """
        result = store.execute(
            delete_query,
            {
                "project_id": project_id,
                "file_path": file_path,
                "current_run_id": current_run_id,
            },
        )

        deleted = 0
        while result.has_next():
            result.get_next()
            deleted += 1

        if should_commit:
            tx.commit()

        return deleted

    except Exception as e:
        if should_commit:
            tx.rollback()
        logger.exception(f"Failed to delete stale symbols: {e}")
        raise
