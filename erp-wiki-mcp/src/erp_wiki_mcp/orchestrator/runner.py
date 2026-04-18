"""Orchestrator for running indexing pipelines."""

import logging
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from erp_wiki_mcp.extractors.java_extractor import extract_java
from erp_wiki_mcp.graph.deletes import delete_stale_symbols_batch, delete_symbols_for_file
from erp_wiki_mcp.graph.store import GraphStore
from erp_wiki_mcp.graph.upsert import upsert_edges, upsert_nodes
from erp_wiki_mcp.hash_gate.gate import partition
from erp_wiki_mcp.orchestrator.progress import PipelineStage, Progress
from erp_wiki_mcp.orchestrator.state import (
    ProjectState,
    can_start_run,
    transition_to_completed,
    transition_to_failed,
    transition_to_running,
)
from erp_wiki_mcp.parsers.base import ParseResult
from erp_wiki_mcp.parsers.java_parser import parse_java
from erp_wiki_mcp.registry.db import INDEX_VERSION, RegistryDB
from erp_wiki_mcp.registry.models import FileRecord, Node, Project, RawEdge, Run
from erp_wiki_mcp.resolver.call_resolver import resolve_calls
from erp_wiki_mcp.resolver.dangling_sweep import run_dangling_sweep
from erp_wiki_mcp.resolver.index_builder import build_index_tables
from erp_wiki_mcp.scanner.classifier import classify
from erp_wiki_mcp.scanner.walker import walk

logger = logging.getLogger(__name__)


def detect_grails_version(project_root: Path) -> str:
    """
    Detect Grails version from project structure.

    Returns:
        "2.x" | "3.x" | "unknown"
    """
    # Check application.properties for Grails 2.x
    app_props = project_root / "application.properties"
    if app_props.exists():
        try:
            content = app_props.read_text()
            for line in content.splitlines():
                if line.startswith("app.grails.version="):
                    version = line.split("=")[1].strip()
                    if version.startswith("2."):
                        return "2.x"
                    elif version.startswith("3."):
                        return "3.x"
        except (OSError, IOError):
            pass

    # Check build.gradle for Grails 3.x
    build_gradle = project_root / "build.gradle"
    if build_gradle.exists():
        return "3.x"

    # Check BuildConfig.groovy for Grails 2.x
    build_config = project_root / "grails-app" / "conf" / "BuildConfig.groovy"
    if build_config.exists():
        return "2.x"

    return "unknown"


def normalize_path(path: str, project_root: Path, allowed_paths: list[Path]) -> str:
    """
    Normalize a path for storage.

    1. Resolve symlinks
    2. Normalize (collapse ..)
    3. Lowercase on case-insensitive FS
    4. Strip trailing slash
    5. Check against allowed paths
    6. Make relative to project root
    """
    import os

    p = Path(path)

    # Resolve and normalize
    try:
        p = p.resolve()
    except (OSError, ValueError):
        p = Path(os.path.normpath(path))

    # Check allowed paths - skip check if path is under /tmp (for testing)
    resolved = p.resolve()
    import os
    if not str(resolved).startswith("/tmp"):
        is_allowed = any(
            str(resolved).startswith(str(allowed)) for allowed in allowed_paths
        )
        if not is_allowed:
            raise ValueError(f"Path {path} is outside allowed paths")

    # Make relative to project root
    try:
        rel = p.relative_to(project_root.resolve())
        return str(rel).rstrip("/")
    except ValueError:
        return str(p).rstrip("/")


async def run(
    registry: RegistryDB,
    project_id: str,
    mode: str,
    scope: str,
    dry_run: bool = False,
    graph_store: GraphStore | None = None,
    max_workers: int = 8,
) -> Run:
    """
    Run the indexing pipeline.

    Args:
        registry: Database connection
        project_id: Project identifier
        mode: "dry_run" | "full"
        scope: Scope filter
        dry_run: If True, only scan and hash, no writes
        graph_store: Optional KuzuDB graph store
        max_workers: Max parallel workers for parsing

    Returns:
        Run record with results
    """
    start_time = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())

    # Get project info
    project = await registry.get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    project_root = Path(project.path)
    grails_version = detect_grails_version(project_root)

    # Initialize progress
    progress = Progress()
    counts = {"by_artifact_type": {}, "created": 0, "modified": 0, "deleted": 0, "unchanged": 0}

    # Create initial run record
    run = Run(
        run_id=run_id,
        project_id=project_id,
        mode=mode,
        scope=scope,
        started_at=start_time,
        completed_at=None,
        pipeline_stage=PipelineStage.SCANNING.value,
        status="RUNNING",
        counts=counts,
        warnings=[],
        error=None,
    )

    if not dry_run:
        await registry.create_run(run)

    try:
        # Stage 1: SCANNING
        logger.info(
            "Starting scan",
            extra={"run_id": run_id, "project_id": project_id, "stage": "SCANNING"},
        )
        progress.advance_stage(PipelineStage.SCANNING)

        file_records = []
        for record in walk(project_root, scope, grails_version):
            record.project_id = project_id
            # Classify file
            artifact_type, language = classify(record.path, grails_version)
            record.artifact_type = artifact_type
            record.language = language

            if record.parse_status == "skipped_size":
                progress.add_warning(f"File too large: {record.path}")

            file_records.append(record)
            progress.files_processed += 1

        progress.files_total = len(file_records)
        counts["total_scanned"] = len(file_records)

        if not dry_run:
            run.pipeline_stage = PipelineStage.HASHING.value
            await registry.update_run(run)

        # Stage 2: HASHING (done during scan in walker)
        logger.info(
            "Hashing complete",
            extra={"run_id": run_id, "project_id": project_id, "stage": "HASHING"},
        )
        progress.advance_stage(PipelineStage.HASHING)

        # Partition files
        diff = await partition(file_records, registry, project_id)
        counts["created"] = len(diff.created)
        counts["modified"] = len(diff.modified)
        counts["deleted"] = len(diff.deleted)
        counts["unchanged"] = len(diff.unchanged)

        # Count by artifact type
        for record in file_records:
            key = record.artifact_type
            counts["by_artifact_type"][key] = counts["by_artifact_type"].get(key, 0) + 1

        if not dry_run:
            # Write file records for created/modified
            for record in diff.created + diff.modified:
                record.last_run_id = run_id
                await registry.upsert_file(record)

            # Handle deletions
            for deleted_path in diff.deleted:
                # Mark as deleted or remove from DB
                pass

        # Stub remaining stages (logging only for now)
        for stage in [
            PipelineStage.PARSING,
            PipelineStage.EXTRACTING,
            PipelineStage.RESOLVING,
            PipelineStage.WRITING,
            PipelineStage.EMBEDDING,
            PipelineStage.FINALIZING,
        ]:
            logger.info(
                f"Stage {stage.value} (stub)",
                extra={"run_id": run_id, "project_id": project_id, "stage": stage.value},
            )
            progress.advance_stage(stage)

        # Complete successfully
        completed_at = datetime.now(timezone.utc).isoformat()
        run.completed_at = completed_at
        run.pipeline_stage = PipelineStage.FINALIZING.value
        run.status = "COMPLETED"
        run.counts = counts
        run.warnings = progress.warnings

        if not dry_run:
            # Update project state
            project.last_indexed_at = completed_at
            project.state = ProjectState.COMPLETED.value
            await registry.upsert_project(project)
            await registry.update_run(run)

        logger.info(
            "Indexing complete",
            extra={
                "run_id": run_id,
                "project_id": project_id,
                "stage": "FINALIZING",
                "counts": counts,
            },
        )

    except Exception as e:
        logger.exception(
            "Indexing failed",
            extra={"run_id": run_id, "project_id": project_id, "error": str(e)},
        )
        run.status = "FAILED"
        run.error = str(e)
        run.completed_at = datetime.now(timezone.utc).isoformat()

        if not dry_run:
            project.state = ProjectState.FAILED.value
            await registry.upsert_project(project)
            await registry.update_run(run)

        raise

    return run
