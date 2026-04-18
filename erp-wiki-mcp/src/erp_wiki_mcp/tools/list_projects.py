"""MCP tool: list_projects."""

import logging

from erp_wiki_mcp.registry.db import RegistryDB
import aiosqlite

logger = logging.getLogger(__name__)


async def list_projects(registry: RegistryDB) -> list[dict]:
    """
    List all indexed projects.

    Args:
        registry: Database connection

    Returns:
        List of project summaries with id, path, state, and last_indexed_at
    """
    async with aiosqlite.connect(registry.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT project_id, path, normalized_path, state, 
                   last_indexed_at, index_version
            FROM projects
            ORDER BY last_indexed_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            
            return [
                {
                    "project_id": row["project_id"],
                    "path": row["path"],
                    "normalized_path": row["normalized_path"],
                    "state": row["state"],
                    "last_indexed_at": row["last_indexed_at"],
                    "index_version": row["index_version"],
                }
                for row in rows
            ]
