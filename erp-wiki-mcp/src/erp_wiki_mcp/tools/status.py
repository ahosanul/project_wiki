"""MCP tool: status."""

import logging

from erp_wiki_mcp.registry.db import RegistryDB
from erp_wiki_mcp.registry.models import Run

logger = logging.getLogger(__name__)


async def get_status(
    registry: RegistryDB,
    run_id: str | None = None,
    project_id: str | None = None,
) -> dict:
    """
    Get status of a run or project.

    Args:
        registry: Database connection
        run_id: Optional run ID to query
        project_id: Optional project ID to query (if run_id not provided)

    Returns:
        Dict with project state, pipeline_stage, graph stats, last_error
    """
    if run_id:
        # Get specific run
        run = await registry.get_run(run_id)
        if run is None:
            return {"error": f"Run not found: {run_id}"}

        # Get project for additional context
        project = await registry.get_project(run.project_id)

        return {
            "run_id": run.run_id,
            "project_id": run.project_id,
            "state": project.state if project else "UNKNOWN",
            "pipeline_stage": run.pipeline_stage,
            "status": run.status,
            "mode": run.mode,
            "scope": run.scope,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "counts": run.counts,
            "warnings": run.warnings,
            "last_error": run.error,
            "graph_stats": {
                "nodes": 0,  # Placeholder for future implementation
                "edges": 0,
            },
        }

    elif project_id:
        # Get latest run for project
        project = await registry.get_project(project_id)
        if project is None:
            return {"error": f"Project not found: {project_id}"}

        # For now, return project state directly
        return {
            "project_id": project_id,
            "state": project.state,
            "path": project.path,
            "normalized_path": project.normalized_path,
            "grails_version": project.language_profile.get("grails_version", "unknown"),
            "index_version": project.index_version,
            "created_at": project.created_at,
            "last_indexed_at": project.last_indexed_at,
            "last_commit_sha": project.last_commit_sha,
            "graph_stats": {
                "nodes": 0,
                "edges": 0,
            },
            "last_error": None,
        }

    else:
        return {"error": "Either run_id or project_id must be provided"}
