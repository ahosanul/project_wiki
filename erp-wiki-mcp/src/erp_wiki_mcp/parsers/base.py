"""Base parser module."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ParseResult:
    """Result of parsing a file."""

    file_path: str
    language: str
    artifact_type: str
    status: str  # ok | partial | failed | skipped_size
    error: str | None
    tree: Any  # language-specific AST
    raw_source: bytes  # nulled after extraction
