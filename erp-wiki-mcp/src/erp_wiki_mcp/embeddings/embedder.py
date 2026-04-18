"""Embedder with swappable backends."""

import os
import time
from typing import Callable

# Default to local backend
BACKEND = os.getenv("MCP_EMBEDDING_BACKEND", "local")

_embed_fn: Callable[[list[str]], list[list[float]]] | None = None


def get_embedder() -> Callable[[list[str]], list[list[float]]]:
    """Get the embedding function based on backend config."""
    global _embed_fn
    if _embed_fn is not None:
        return _embed_fn
    
    if BACKEND == "openai":
        try:
            import openai
            api_key = os.getenv("MCP_OPENAI_API_KEY")
            if not api_key:
                raise ValueError("MCP_OPENAI_API_KEY not set")
            
            def openai_embed(texts: list[str]) -> list[list[float]]:
                max_retries = 3
                base_delay = 2
                
                for attempt in range(max_retries):
                    try:
                        response = openai.embeddings.create(
                            input=texts,
                            model="text-embedding-3-small"
                        )
                        return [r.embedding for r in response.data]
                    except Exception as e:
                        if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            time.sleep(delay)
                        else:
                            raise
                return []
            
            _embed_fn = openai_embed
            return openai_embed
        except ImportError:
            pass
    
    # Local backend (default)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        def local_embed(texts: list[str]) -> list[list[float]]:
            embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)
            return embeddings.tolist()
        
        _embed_fn = local_embed
        return local_embed
    except ImportError:
        # Fallback: return zero vectors
        def fallback_embed(texts: list[str]) -> list[list[float]]:
            return [[0.0] * 384 for _ in texts]
        
        _embed_fn = fallback_embed
        return fallback_embed


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts."""
    return get_embedder()(texts)
