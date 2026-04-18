"""MCP tool: index_project."""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from erp_wiki_mcp.config import settings
from erp_wiki_mcp.orchestrator.runner import detect_grails_version, normalize_path, run
from erp_wiki_mcp.registry.db import INDEX_VERSION, RegistryDB
from erp_wiki_mcp.registry.models import Project

logger = logging.getLogger(__name__)


async def index_project(
    registry: RegistryDB,
    path: str,
    mode: str = "dry_run",
    scope: str = "full",
    profile_override: dict | None = None,
) -> dict:
    """
    Index a project and return results.

    Args:
        registry: Database connection
        path: Path to the project root
        mode: "dry_run" | "full"
        scope: Scope filter (full, file:<rel>, module:<dir>, etc.)
        profile_override: Optional language profile override

    Returns:
        Dict with run_id, state, file counts, duration_ms, warnings
    """
    start_time = time.time()

    # Normalize and validate path
    project_root = Path(path).expanduser().resolve()
    allowed_paths = settings.get_allowed_paths()

    try:
        normalized = normalize_path(str(project_root), project_root, allowed_paths)
    except ValueError as e:
        return {
            "error": str(e),
            "state": "FAILED",
        }

    # Generate project ID from normalized path
    project_id = f"proj_{abs(hash(normalized)) % 10**12}"

    # Detect Grails version
    grails_version = detect_grails_version(project_root)

    # Get or create project record
    project = await registry.get_project(project_id)
    now = datetime.now(timezone.utc).isoformat()

    if project is None:
        # Create new project
        project = Project(
            project_id=project_id,
            path=str(project_root),
            normalized_path=normalized,
            language_profile=profile_override or {"grails_version": grails_version},
            index_version=INDEX_VERSION,
            state="NEW",
            created_at=now,
            last_indexed_at=now,
            last_commit_sha=None,
        )
        await registry.upsert_project(project)
        logger.info(f"Created new project: {project_id}")
    else:
        # Update existing project
        project.last_indexed_at = now
        project.language_profile = profile_override or project.language_profile
        await registry.upsert_project(project)

    # Run the indexing pipeline
    dry_run = mode == "dry_run"
    result_run = await run(registry, project_id, mode, scope, dry_run=dry_run)

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "run_id": result_run.run_id,
        "project_id": project_id,
        "state": result_run.status,
        "file_counts": result_run.counts.get("by_artifact_type", {}),
        "created": result_run.counts.get("created", 0),
        "modified": result_run.counts.get("modified", 0),
        "deleted": result_run.counts.get("deleted", 0),
        "unchanged": result_run.counts.get("unchanged", 0),
        "duration_ms": duration_ms,
        "warnings": result_run.warnings,
        "error": result_run.error,
    }
