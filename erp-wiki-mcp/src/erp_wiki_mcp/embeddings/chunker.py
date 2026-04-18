"""Chunker for embedding pipeline."""

from dataclasses import dataclass
from typing import Any

from erp_wiki_mcp.registry.models import Node


@dataclass
class Chunk:
    symbol_id: str
    chunk_type: str  # docstring | method_body | gsp_text | config_comment
    text: str
    metadata: dict


def chunk(node: Node, raw_source: bytes | None = None) -> list[Chunk]:
    """Generate chunks from a node for embedding."""
    chunks: list[Chunk] = []
    
    # Docstring chunk
    if node.docstring:
        chunks.append(Chunk(
            symbol_id=node.id,
            chunk_type="docstring",
            text=node.docstring,
            metadata={
                "symbol_id": node.id,
                "chunk_type": "docstring",
                "project_id": node.project_id,
                "kind": node.kind,
                "file_path": node.file_path,
                "line_start": node.line_start,
            },
        ))
    
    # Method/action body chunk
    if node.kind in ("method", "action") and raw_source:
        # In practice, would extract actual source range
        # For now, skip if no source provided
        pass
    
    # GSP static text chunk
    if node.kind in ("gsp_view", "gsp_layout", "gsp_template"):
        static_text = node.properties.get("static_text", "")
        if static_text:
            chunks.append(Chunk(
                symbol_id=node.id,
                chunk_type="gsp_text",
                text=static_text[:2000],  # Limit size
                metadata={
                    "symbol_id": node.id,
                    "chunk_type": "gsp_text",
                    "project_id": node.project_id,
                    "kind": node.kind,
                    "file_path": node.file_path,
                    "line_start": node.line_start,
                },
            ))
    
    # Config comment chunk (if captured)
    if node.kind == "config_key":
        # Config keys themselves are short, but could embed comments
        pass
    
    return chunks
