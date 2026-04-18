"""Data models for the registry."""

from dataclasses import dataclass, field


@dataclass
class Project:
    """Represents an indexed project."""

    project_id: str
    path: str
    normalized_path: str
    language_profile: dict
    index_version: int
    state: str
    created_at: str
    last_indexed_at: str
    last_commit_sha: str | None = None


@dataclass
class FileRecord:
    """Represents a file in the project."""

    project_id: str
    path: str
    abs_path: str
    size: int
    mtime: float
    content_hash: str | None
    language: str
    artifact_type: str
    parse_status: str
    last_run_id: str | None = None


@dataclass
class Run:
    """Represents an indexing run."""

    run_id: str
    project_id: str
    mode: str
    scope: str
    started_at: str
    completed_at: str | None
    pipeline_stage: str
    status: str
    counts: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: str | None = None


@dataclass
class Node:
    """Represents a node in the knowledge graph."""

    id: str
    kind: str
    name: str
    fqn: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    project_id: str
    last_run_id: str
    docstring: str | None = None
    source_hash: str | None = None
    properties: dict = field(default_factory=dict)
    grails_version: str | None = None


@dataclass
class RawEdge:
    """Represents an edge between nodes."""

    source_id: str
    target_id: str | None
    target_hint: str | None
    type: str
    file_path: str
    line: int
    confidence: float
    extractor: str
