# RAG Store — builds and persists the FAISS vector index
# Fetches all task titles from Notion, chunks + embeds them,
# and saves the index + metadata to disk.
#
# Files saved:
#   rag/index.faiss   — the vector index
#   rag/titles.json   — task titles mapped to index positions

import os
import json
import httpx
import faiss
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

NOTION_API_KEY     = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Paths for persisted index files
INDEX_DIR   = Path(__file__).parent
INDEX_PATH  = INDEX_DIR / "index.faiss"
TITLES_PATH = INDEX_DIR / "titles.json"

_embedder = SentenceTransformer("all-MiniLM-L6-v2")


def _fetch_notion_tasks() -> list[str]:
    """Fetch all task titles from Notion database."""
    try:
        response = httpx.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            headers=HEADERS,
            json={"page_size": 100},
            timeout=10,
        )
        response.raise_for_status()
        pages = response.json().get("results", [])
        titles = []
        for page in pages:
            title_prop = page.get("properties", {}).get("", {})
            title_list = title_prop.get("title", [])
            if title_list:
                text = title_list[0].get("plain_text", "").strip()
                if text:
                    titles.append(text)
        return titles
    except Exception as e:
        print(f"[RAG Store] Failed to fetch Notion tasks: {e}")
        return []


def build_index() -> int:
    """
    Fetch tasks from Notion, embed them, build FAISS index, save to disk.
    Returns number of tasks indexed.
    """
    titles = _fetch_notion_tasks()

    if not titles:
        print("[RAG Store] No tasks found in Notion — index not built.")
        return 0

    print(f"[RAG Store] Embedding {len(titles)} tasks...")

    # Embed all titles
    embeddings = _embedder.encode(titles, convert_to_numpy=True, show_progress_bar=False)
    embeddings = embeddings.astype(np.float32)

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    # Build flat inner-product index (cosine on normalized = cosine similarity)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Save index to disk
    faiss.write_index(index, str(INDEX_PATH))

    # Save titles metadata
    with open(TITLES_PATH, "w") as f:
        json.dump(titles, f, indent=2)

    print(f"[RAG Store] Index saved → {INDEX_PATH} ({len(titles)} tasks)")
    return len(titles)


def index_exists() -> bool:
    return INDEX_PATH.exists() and TITLES_PATH.exists()


if __name__ == "__main__":
    build_index()
