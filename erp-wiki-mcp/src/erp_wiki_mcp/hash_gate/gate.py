"""Hash gate for detecting file changes."""

from dataclasses import dataclass, field

from erp_wiki_mcp.registry.db import INDEX_VERSION, RegistryDB
from erp_wiki_mcp.registry.models import FileRecord


@dataclass
class DiffResult:
    """Result of partitioning files by change status."""

    created: list[FileRecord] = field(default_factory=list)
    modified: list[FileRecord] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    unchanged: list[FileRecord] = field(default_factory=list)


async def partition(
    file_records: list[FileRecord], registry: RegistryDB, project_id: str
) -> DiffResult:
    """
    Partition files into created, modified, deleted, and unchanged.

    Args:
        file_records: Current files from scanner
        registry: Database connection
        project_id: Project identifier

    Returns:
        DiffResult with partitioned files
    """
    result = DiffResult()

    # Get existing files from registry
    existing_files_list = await registry.get_files_for_project(project_id)
    existing_files = {f.path: f for f in existing_files_list}

    # Check if index version requires re-index
    project = await registry.get_project(project_id)
    force_reindex = project is not None and project.index_version < INDEX_VERSION

    current_paths = set()

    for record in file_records:
        current_paths.add(record.path)

        if force_reindex:
            # All files treated as modified if index version changed
            result.modified.append(record)
        elif record.path not in existing_files:
            # New file
            result.created.append(record)
        else:
            existing = existing_files[record.path]
            if record.content_hash != existing.content_hash:
                # Hash changed
                result.modified.append(record)
            else:
                # Unchanged
                result.unchanged.append(record)

    # Find deleted files
    for path in existing_files:
        if path not in current_paths:
            result.deleted.append(path)

    return result
