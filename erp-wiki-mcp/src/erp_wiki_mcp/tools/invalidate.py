"""Invalidate tool for cache management."""

from erp_wiki_mcp.hash_gate.gate import invalidate_hash_cache
from erp_wiki_mcp.registry.db import RegistryDB


async def handler(
    project_id: str,
    scope: str = "all",
) -> dict:
    """
    Invalidate cached data to force re-indexing.
    
    Args:
        project_id: Project identifier
        scope: "all" | "file:<path>" | "module:<dir>" | "hashes"
    
    Returns:
        {invalidated_files[], next_index_mode}
    """
    registry = RegistryDB()
    
    invalidated_files = []
    next_index_mode = "full"
    
    if scope == "all":
        # Clear all hash entries for project
        await invalidate_hash_cache(project_id, None)
        next_index_mode = "full"
    elif scope.startswith("file:"):
        file_path = scope[5:]
        await invalidate_hash_cache(project_id, file_path)
        invalidated_files.append(file_path)
        next_index_mode = "incremental"
    elif scope.startswith("module:"):
        module_dir = scope[7:]
        await invalidate_hash_cache(project_id, module_dir)
        next_index_mode = "incremental"
    elif scope == "hashes":
        # Clear only hash cache, keep symbols
        await invalidate_hash_cache(project_id, None, clear_only_hashes=True)
        next_index_mode = "incremental"
    
    return {
        "invalidated_files": invalidated_files,
        "next_index_mode": next_index_mode,
    }
