"""Graph delete operations for deleted/modified files."""

import logging

from erp_wiki_mcp.graph.store import GraphStore

logger = logging.getLogger(__name__)


def delete_symbols_for_file(
    store: GraphStore,
    project_id: str,
    file_path: str,
    tx=None,
) -> int:
    """
    Delete all symbols and edges for a deleted file.

    For DELETED files:
    1. Find all Symbol nodes where project_id=X AND file_path=deleted_file
    2. DELETE all Edge records where source_id IN found OR target_id IN found
    3. DELETE Symbol nodes

    Args:
        store: Graph store
        project_id: Project ID
        file_path: File path to delete

    Returns:
        Number of symbols deleted
    """
    should_commit = tx is None
    if should_commit:
        tx = store.begin_transaction()

    try:
        # Delete edges first (cascade will handle this, but being explicit)
        delete_edges_query = """
        MATCH (s:Symbol {project_id: $project_id, file_path: $file_path})
        MATCH ()-[e:Edge]-(s)
        DELETE e
        """
        store.execute(
            delete_edges_query,
            {"project_id": project_id, "file_path": file_path},
        )

        # Delete symbols
        delete_query = """
        MATCH (s:Symbol {project_id: $project_id, file_path: $file_path})
        DELETE s
        """
        result = store.execute(
            delete_query,
            {"project_id": project_id, "file_path": file_path},
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
        logger.exception(f"Failed to delete symbols for file {file_path}: {e}")
        raise


def delete_stale_symbols_batch(
    store: GraphStore,
    project_id: str,
    modified_files: list[str],
    current_run_id: str,
    tx=None,
) -> int:
    """
    Delete stale symbols for multiple modified files.

    For MODIFIED files:
    DELETE Symbol where project_id=X AND file_path=modified_file AND last_run_id != current_run_id

    Args:
        store: Graph store
        project_id: Project ID
        modified_files: List of modified file paths
        current_run_id: Current run ID

    Returns:
        Total number of symbols deleted
    """
    total_deleted = 0

    should_commit = tx is None
    if should_commit:
        tx = store.begin_transaction()

    try:
        for file_path in modified_files:
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

            total_deleted += deleted

        if should_commit:
            tx.commit()

        return total_deleted

    except Exception as e:
        if should_commit:
            tx.rollback()
        logger.exception(f"Failed to delete stale symbols: {e}")
        raise
