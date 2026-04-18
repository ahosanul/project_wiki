"""Rebuild tool for incremental or full re-indexing."""

from erp_wiki_mcp.orchestrator.runner import run
from erp_wiki_mcp.registry.db import RegistryDB
from erp_wiki_mcp.registry.models import Run


async def handler(
    project_id: str,
    scope: str = "incremental",
    watch: bool = False,
) -> dict:
    """
    Re-index a project with specified scope.
    
    Args:
        project_id: Project identifier
        scope: "incremental" | "full" | "file:<path>" | "module:<dir>" | "git:<commit_range>"
        watch: If True, start file watcher after rebuild
    
    Returns:
        Same shape as index_project output
    """
    registry = RegistryDB()
    
    # Handle git scope
    if scope.startswith("git:"):
        import subprocess
        commit_range = scope[4:]
        try:
            result = subprocess.run(
                ["git", "-C", str(registry.data_dir), "diff", "--name-only", commit_range],
                capture_output=True,
                text=True,
                check=True,
            )
            files = result.stdout.strip().split("\n")
            scope = f"files:{','.join(files)}"
        except subprocess.CalledProcessError:
            pass
    
    # Run pipeline
    run_result = await run(
        registry=registry,
        project_id=project_id,
        mode="full" if scope == "full" else "auto",
        scope=scope,
        dry_run=False,
    )
    
    return {
        "run_id": run_result.run_id,
        "state": run_result.status,
        "file_counts_by_artifact_type": run_result.counts.get("by_artifact_type", {}),
        "symbols_added": run_result.counts.get("created", 0),
        "symbols_updated": run_result.counts.get("modified", 0),
        "symbols_removed": run_result.counts.get("deleted", 0),
        "edges_added": run_result.counts.get("edges_added", 0),
        "edges_updated": run_result.counts.get("edges_updated", 0),
        "edges_removed": run_result.counts.get("edges_removed", 0),
        "duration_ms": 0,
        "warnings": run_result.warnings,
    }
