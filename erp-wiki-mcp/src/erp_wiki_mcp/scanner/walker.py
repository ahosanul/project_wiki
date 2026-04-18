"""File walker for scanning project directories."""

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import blake3
from gitignore_parser import parse_gitignore

from erp_wiki_mcp.config import settings
from erp_wiki_mcp.registry.models import FileRecord


# Hardcoded ignore patterns
HARDCODED_IGNORE = {
    "node_modules",
    ".idea",
    ".git",
}

HARDCODED_GLOBS_3X = {
    "build/",
    "target/",
    "out/",
    ".gradle/",
    "dist/",
}

HARDCODED_GLOBS_2X = {
    "target/",
    ".grails/",
    "staging/",
    "web-app/WEB-INF/classes/",
}

EXTENSION_IGNORES = {
    ".class",
    ".jar",
    ".war",
    ".ear",
    ".min.js",
    ".min.css",
}


@dataclass
class DiffResult:
    """Result of hashing files against registry."""

    created: list[FileRecord] = field(default_factory=list)
    modified: list[FileRecord] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    unchanged: list[FileRecord] = field(default_factory=list)


def _should_ignore_hardcoded(rel_path: str, grails_version: str) -> bool:
    """Check if path matches hardcoded ignore patterns."""
    parts = rel_path.split(os.sep)

    # Check directory names
    for part in parts:
        if part in HARDCODED_IGNORE:
            return True

    # Check extension ignores
    path_lower = rel_path.lower()
    for ext in EXTENSION_IGNORES:
        if path_lower.endswith(ext):
            return True

    # Version-specific ignores
    globs = HARDCODED_GLOBS_3X if grails_version == "3.x" else HARDCODED_GLOBS_2X
    for glob in globs:
        if rel_path.startswith(glob.rstrip("/")) or rel_path.startswith(
            glob.rstrip("/") + os.sep
        ):
            return True

    return False


def _compute_blake3(file_path: Path) -> str:
    """Compute BLAKE3 hash of file contents."""
    hasher = blake3.blake3()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def walk(project_root: Path, scope: str, grails_version: str) -> Iterator[FileRecord]:
    """
    Walk project directory and yield FileRecords.

    Args:
        project_root: Root path of the project
        scope: Scope filter (full, file:<rel>, module:<dir>, etc.)
        grails_version: Detected Grails version ("2.x" | "3.x" | "unknown")

    Yields:
        FileRecord for each file found
    """
    project_root = project_root.resolve()
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024

    # Parse .gitignore
    gitignore_path = project_root / ".gitignore"
    matches_gitignore = None
    if gitignore_path.exists():
        matches_gitignore = parse_gitignore(str(gitignore_path))

    # Parse .mcpignore
    mcpignore_path = project_root / ".mcpignore"
    matches_mcpignore = None
    if mcpignore_path.exists():
        matches_mcpignore = parse_gitignore(str(mcpignore_path))

    # Determine scope filter
    scope_filter = None
    if scope.startswith("file:"):
        scope_filter = scope[5:]
    elif scope.startswith("module:"):
        scope_filter = scope[7:]

    for root, dirs, files in os.walk(project_root):
        # Filter directories in-place
        dirs[:] = [
            d
            for d in dirs
            if d not in HARDCODED_IGNORE
        ]

        for filename in files:
            abs_path = Path(root) / filename
            rel_path = abs_path.relative_to(project_root)
            rel_path_str = str(rel_path)

            # Check hardcoded ignores
            if _should_ignore_hardcoded(rel_path_str, grails_version):
                continue

            # Check .gitignore
            if matches_gitignore and matches_gitignore(str(abs_path)):
                continue

            # Check .mcpignore
            if matches_mcpignore and matches_mcpignore(str(abs_path)):
                continue

            # Apply scope filter
            if scope_filter:
                if scope.startswith("file:") and rel_path_str != scope_filter:
                    continue
                if scope.startswith("module:") and not rel_path_str.startswith(
                    scope_filter
                ):
                    continue

            # Get file stats
            try:
                stat = abs_path.stat()
            except OSError:
                continue

            size = stat.st_size
            mtime = stat.st_mtime

            # Check size limit
            parse_status = "pending"
            if size > max_size_bytes:
                parse_status = "skipped_size"

            # Compute hash
            content_hash = None
            if parse_status == "pending":
                try:
                    content_hash = _compute_blake3(abs_path)
                except (OSError, IOError):
                    parse_status = "error_read"

            yield FileRecord(
                project_id="",  # Will be set by caller
                path=rel_path_str,
                abs_path=str(abs_path),
                size=size,
                mtime=mtime,
                content_hash=content_hash,
                language="",  # Will be set by classifier
                artifact_type="",  # Will be set by classifier
                parse_status=parse_status,
                last_run_id=None,
            )
