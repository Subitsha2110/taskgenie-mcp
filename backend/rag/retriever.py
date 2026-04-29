# RAG Retriever — loads persisted FAISS index and searches for similar tasks
# If index doesn't exist yet, builds it on first call.

import json
import faiss
import numpy as np
from pathlib import Path
from typing import Any
from sentence_transformers import SentenceTransformer

INDEX_PATH  = Path(__file__).parent / "index.faiss"
TITLES_PATH = Path(__file__).parent / "titles.json"

_embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Similarity threshold — above this = duplicate
DUPLICATE_THRESHOLD = 0.85


def _load_index():
    """Load FAISS index and titles from disk."""
    index  = faiss.read_index(str(INDEX_PATH))
    with open(TITLES_PATH) as f:
        titles = json.load(f)
    return index, titles


def check_duplicate(new_task_title: str) -> dict[str, Any]:
    """
    Search the persisted FAISS index for tasks similar to new_task_title.

    Flow:
      1. Load index.faiss + titles.json from disk
      2. Embed the new task title
      3. Search top-1 nearest neighbour
      4. Return similarity score + match

    Returns:
        {
            "is_duplicate": bool,
            "similar_task": str or None,
            "similarity_score": float
        }
    """
    # Build index if it doesn't exist yet
    if not INDEX_PATH.exists():
        from rag.store import build_index
        built = build_index()
        if built == 0:
            return {"is_duplicate": False, "similar_task": None, "similarity_score": 0.0}

    try:
        index, titles = _load_index()
    except Exception as e:
        return {"is_duplicate": False, "similar_task": None, "similarity_score": 0.0}

    if not titles:
        return {"is_duplicate": False, "similar_task": None, "similarity_score": 0.0}

    # Embed + normalize new task
    new_embedding = _embedder.encode([new_task_title], convert_to_numpy=True).astype(np.float32)
    faiss.normalize_L2(new_embedding)

    # Search
    scores, indices = index.search(new_embedding, k=1)
    top_score = float(scores[0][0])
    top_match = titles[indices[0][0]]

    is_duplicate = top_score >= DUPLICATE_THRESHOLD

    return {
        "is_duplicate": is_duplicate,
        "similar_task": top_match if is_duplicate else None,
        "similarity_score": round(top_score, 3),
    }


def rebuild_index():
    """Call this after a new task is created to keep the index fresh."""
    from rag.store import build_index
    return build_index()
