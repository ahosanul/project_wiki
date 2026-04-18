"""SQLite registry for project metadata."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from erp_wiki_mcp.registry.models import FileRecord, Project, Run


# Current schema version - increment to force re-index
INDEX_VERSION = 1

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    normalized_path TEXT NOT NULL,
    language_profile TEXT NOT NULL,
    index_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_indexed_at TEXT NOT NULL,
    last_commit_sha TEXT
)
"""

CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS files (
    project_id TEXT NOT NULL,
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    content_hash TEXT NOT NULL,
    language TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    parse_status TEXT NOT NULL,
    last_run_id TEXT,
    PRIMARY KEY (project_id, path)
)
"""

CREATE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    scope TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    pipeline_stage TEXT NOT NULL,
    status TEXT NOT NULL,
    counts TEXT NOT NULL,
    warnings TEXT NOT NULL,
    error TEXT
)
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id);
"""


class RegistryDB:
    """Async SQLite wrapper for the registry."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(CREATE_PROJECTS_TABLE)
            await conn.execute(CREATE_FILES_TABLE)
            await conn.execute(CREATE_RUNS_TABLE)
            await conn.execute(CREATE_INDEXES)
            await conn.commit()

    async def get_project(self, project_id: str) -> Project | None:
        """Get project by ID."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM projects WHERE project_id = ?", (project_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_project(row)

    async def upsert_project(self, project: Project) -> None:
        """Insert or update a project."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO projects 
                (project_id, path, normalized_path, language_profile, index_version, 
                 state, created_at, last_indexed_at, last_commit_sha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    project.path,
                    project.normalized_path,
                    json.dumps(project.language_profile),
                    project.index_version,
                    project.state,
                    project.created_at,
                    project.last_indexed_at,
                    project.last_commit_sha,
                ),
            )
            await conn.commit()

    async def get_files_for_project(self, project_id: str) -> list[FileRecord]:
        """Get all files for a project."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM files WHERE project_id = ?", (project_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_file(row) for row in rows]

    async def upsert_file(self, file_record: FileRecord) -> None:
        """Insert or update a file record."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO files 
                (project_id, path, size, mtime, content_hash, language, 
                 artifact_type, parse_status, last_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_record.project_id,
                    file_record.path,
                    file_record.size,
                    file_record.mtime,
                    file_record.content_hash or "",
                    file_record.language,
                    file_record.artifact_type,
                    file_record.parse_status,
                    file_record.last_run_id,
                ),
            )
            await conn.commit()

    async def create_run(self, run: Run) -> None:
        """Create a new run record."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO runs 
                (run_id, project_id, mode, scope, started_at, completed_at, 
                 pipeline_stage, status, counts, warnings, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.project_id,
                    run.mode,
                    run.scope,
                    run.started_at,
                    run.completed_at,
                    run.pipeline_stage,
                    run.status,
                    json.dumps(run.counts),
                    json.dumps(run.warnings),
                    run.error,
                ),
            )
            await conn.commit()

    async def update_run(self, run: Run) -> None:
        """Update an existing run record."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE runs SET 
                    completed_at = ?, pipeline_stage = ?, status = ?, 
                    counts = ?, warnings = ?, error = ?
                WHERE run_id = ?
                """,
                (
                    run.completed_at,
                    run.pipeline_stage,
                    run.status,
                    json.dumps(run.counts),
                    json.dumps(run.warnings),
                    run.error,
                    run.run_id,
                ),
            )
            await conn.commit()

    async def get_run(self, run_id: str) -> Run | None:
        """Get run by ID."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_run(row)

    @staticmethod
    def _row_to_project(row: aiosqlite.Row) -> Project:
        return Project(
            project_id=row["project_id"],
            path=row["path"],
            normalized_path=row["normalized_path"],
            language_profile=json.loads(row["language_profile"]),
            index_version=row["index_version"],
            state=row["state"],
            created_at=row["created_at"],
            last_indexed_at=row["last_indexed_at"],
            last_commit_sha=row["last_commit_sha"],
        )

    @staticmethod
    def _row_to_file(row: aiosqlite.Row) -> FileRecord:
        return FileRecord(
            project_id=row["project_id"],
            path=row["path"],
            abs_path="",  # Not stored in DB
            size=row["size"],
            mtime=row["mtime"],
            content_hash=row["content_hash"],
            language=row["language"],
            artifact_type=row["artifact_type"],
            parse_status=row["parse_status"],
            last_run_id=row["last_run_id"],
        )

    @staticmethod
    def _row_to_run(row: aiosqlite.Row) -> Run:
        return Run(
            run_id=row["run_id"],
            project_id=row["project_id"],
            mode=row["mode"],
            scope=row["scope"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            pipeline_stage=row["pipeline_stage"],
            status=row["status"],
            counts=json.loads(row["counts"]),
            warnings=json.loads(row["warnings"]),
            error=row["error"],
        )
