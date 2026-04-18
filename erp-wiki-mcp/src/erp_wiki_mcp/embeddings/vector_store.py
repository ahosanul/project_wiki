"""Vector store using ChromaDB."""

import os
from dataclasses import dataclass
from pathlib import Path

from erp_wiki_mcp.embeddings.chunker import Chunk
from erp_wiki_mcp.embeddings.embedder import embed

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None


@dataclass
class SearchResult:
    symbol_id: str
    chunk_type: str
    text: str
    distance: float
    metadata: dict


class VectorStore:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.client = None
        self.collections: dict[str, any] = {}
        
        if chromadb:
            self.client = chromadb.Client(Settings(
                persist_directory=str(self.data_dir / "chroma"),
                anonymized_telemetry=False,
            ))
    
    def _get_collection(self, project_id: str):
        """Get or create collection for project."""
        if project_id not in self.collections:
            if self.client:
                self.collections[project_id] = self.client.get_or_create_collection(
                    name=f"project_{project_id}",
                    metadata={"project_id": project_id},
                )
        return self.collections.get(project_id)
    
    def upsert(self, symbol_id: str, chunks: list[Chunk], embeddings: list[list[float]]):
        """Upsert chunks for a symbol."""
        if not self.client or not chunks:
            return
        
        collection = self._get_collection(chunks[0].metadata.get("project_id", ""))
        if not collection:
            return
        
        # Delete existing docs for this symbol
        try:
            collection.delete(where={"symbol_id": symbol_id})
        except Exception:
            pass
        
        # Insert new docs
        ids = [f"{symbol_id}_{i}" for i in range(len(chunks))]
        documents = [c.text for c in chunks]
        metadatas = [c.metadata for c in chunks]
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
    
    def delete(self, symbol_id: str, project_id: str = ""):
        """Delete all chunks for a symbol."""
        if not self.client:
            return
        
        # Try all collections if project_id not specified
        if project_id:
            collection = self._get_collection(project_id)
            if collection:
                try:
                    collection.delete(where={"symbol_id": symbol_id})
                except Exception:
                    pass
        else:
            for coll in self.collections.values():
                try:
                    coll.delete(where={"symbol_id": symbol_id})
                except Exception:
                    pass
    
    def search(
        self,
        query_embedding: list[float],
        project_id: str,
        n_results: int = 10,
        filter: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar chunks."""
        if not self.client:
            return []
        
        collection = self._get_collection(project_id)
        if not collection:
            return []
        
        where = filter if filter else {}
        where["project_id"] = project_id
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            
            if not results or not results["ids"]:
                return []
            
            search_results = []
            for i, ids in enumerate(results["ids"]):
                for j, symbol_id in enumerate(ids):
                    search_results.append(SearchResult(
                        symbol_id=symbol_id,
                        chunk_type=results["metadatas"][i][j].get("chunk_type", ""),
                        text=results["documents"][i][j] or "",
                        distance=results["distances"][i][j] if results["distances"] else 0.0,
                        metadata=results["metadatas"][i][j],
                    ))
            return search_results
        except Exception:
            return []
