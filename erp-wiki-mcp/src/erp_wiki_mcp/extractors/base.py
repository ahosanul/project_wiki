"""Base extractor module."""

from dataclasses import dataclass

from erp_wiki_mcp.registry.models import Node, RawEdge


@dataclass
class ExtractorResult:
    """Result of extracting symbols from a parsed file."""

    nodes: list[Node]
    raw_edges: list[RawEdge]
