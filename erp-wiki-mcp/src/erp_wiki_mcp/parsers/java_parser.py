"""Java parser using tree-sitter."""

import logging
from pathlib import Path

import tree_sitter_java
from tree_sitter import Language, Parser

from erp_wiki_mcp.parsers.base import ParseResult

logger = logging.getLogger(__name__)

# Global parser instance - one per worker process
JAVA_LANGUAGE: Language | None = None
_parser: Parser | None = None


def get_language() -> Language:
    """Get the Java language definition."""
    global JAVA_LANGUAGE
    if JAVA_LANGUAGE is None:
        JAVA_LANGUAGE = Language(tree_sitter_java.language())
    return JAVA_LANGUAGE


def get_parser() -> Parser:
    """Get or create a parser instance."""
    global _parser
    if _parser is None:
        _parser = Parser()
        _parser.language = get_language()
    return _parser


def parse_java(file_path: str, source: bytes, artifact_type: str) -> ParseResult:
    """
    Parse a Java file using tree-sitter.

    Args:
        file_path: Path to the Java file
        source: Source code as bytes
        artifact_type: The artifact type from classifier

    Returns:
        ParseResult with AST tree
    """
    try:
        parser = get_parser()
        tree = parser.parse(source)

        # Check for parsing errors
        status = "partial" if tree.root_node.has_error else "ok"

        return ParseResult(
            file_path=file_path,
            language="java",
            artifact_type=artifact_type,
            status=status,
            error=None,
            tree=tree,
            raw_source=source,
        )
    except Exception as e:
        logger.exception(f"Failed to parse {file_path}: {e}")
        return ParseResult(
            file_path=file_path,
            language="java",
            artifact_type=artifact_type,
            status="failed",
            error=str(e),
            tree=None,
            raw_source=source,
        )
