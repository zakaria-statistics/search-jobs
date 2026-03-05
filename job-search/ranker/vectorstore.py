"""ChromaDB vector store for resume-based semantic job filtering."""

import hashlib
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy imports — these may not be installed
_chromadb = None
_embedding_fn = None


def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import chromadb
        _chromadb = chromadb
    return _chromadb


def _get_embedding_fn(model_name: str, hf_token: str = ""):
    """Return a ChromaDB-compatible embedding function.

    Priority:
      1. Local sentence-transformers (fast, no API calls)
      2. HF Inference API (needs HF_API_TOKEN)
    """
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    # Try local sentence-transformers first
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=model_name)
        logger.info("Using local sentence-transformers for embeddings")
        return _embedding_fn
    except (ImportError, Exception) as e:
        logger.warning(f"sentence-transformers unavailable: {e}")

    # Fallback: HF Inference API
    if hf_token:
        try:
            from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction
            _embedding_fn = HuggingFaceEmbeddingFunction(
                api_key=hf_token,
                model_name=f"sentence-transformers/{model_name}",
            )
            logger.info("Using HF Inference API for embeddings")
            return _embedding_fn
        except (ImportError, Exception) as e:
            logger.warning(f"HF Inference API fallback failed: {e}")

    raise ImportError(
        "No embedding backend available. Install sentence-transformers or set HF_API_TOKEN."
    )


def init_collection(chromadb_dir: str, model_name: str, hf_token: str = ""):
    """Create or load a persistent ChromaDB collection."""
    chromadb = _get_chromadb()
    embed_fn = _get_embedding_fn(model_name, hf_token)

    Path(chromadb_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=chromadb_dir)
    collection = client.get_or_create_collection(
        name="resumes",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── Chunking ────────────────────────────────────────────────────────────────


def _chunk_markdown(text: str, heading_pattern: str = r"^## ") -> list[dict]:
    """Split markdown by heading pattern into chunks with section names."""
    chunks = []
    current_section = "preamble"
    current_lines = []

    for line in text.split("\n"):
        if re.match(heading_pattern, line):
            # Save previous chunk
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append({"section": current_section, "text": body})
            current_section = line.lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Last chunk
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append({"section": current_section, "text": body})

    return chunks


def _infer_stack_and_lang(dir_name: str) -> tuple[str, str]:
    """Infer stack and language from resume directory name.

    Examples: ai_eng_zakaria -> ("ai", "en"), aws_fr_zakaria -> ("aws", "fr")
    """
    parts = dir_name.lower().split("_")
    stack = "general"
    lang = "en"

    if parts[0] in ("ai", "aws", "az", "azure"):
        stack = "azure" if parts[0] == "az" else parts[0]

    for p in parts:
        if p in ("fr",):
            lang = "fr"
        elif p in ("eng", "en"):
            lang = "en"

    return stack, lang


# ── File Hashing ────────────────────────────────────────────────────────────


def _hash_file(filepath: str) -> str:
    return hashlib.md5(Path(filepath).read_bytes()).hexdigest()


def _compute_index_hash(resumes_dir: str, candidate_context: str) -> str:
    """Compute combined hash of all resume files + candidate context."""
    parts = []
    resumes_path = Path(resumes_dir)
    if resumes_path.exists():
        for md_file in sorted(resumes_path.rglob("main.md")):
            parts.append(_hash_file(str(md_file)))
    parts.append(hashlib.md5(candidate_context.encode()).hexdigest())
    return hashlib.md5("".join(parts).encode()).hexdigest()


def needs_reindex(chromadb_dir: str, resumes_dir: str, candidate_context: str) -> bool:
    """Check if resumes have changed since last indexing."""
    hash_file = Path(chromadb_dir) / ".index_hash"
    current_hash = _compute_index_hash(resumes_dir, candidate_context)

    if not hash_file.exists():
        return True

    stored_hash = hash_file.read_text().strip()
    return stored_hash != current_hash


def _save_index_hash(chromadb_dir: str, resumes_dir: str, candidate_context: str):
    """Save the current hash after successful indexing."""
    hash_file = Path(chromadb_dir) / ".index_hash"
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    current_hash = _compute_index_hash(resumes_dir, candidate_context)
    hash_file.write_text(current_hash)


# ── Indexing ────────────────────────────────────────────────────────────────


def index_resumes(collection, resumes_dir: str) -> int:
    """Read all resume main.md files, chunk, and upsert into ChromaDB."""
    resumes_path = Path(resumes_dir)
    if not resumes_path.exists():
        logger.warning(f"Resumes directory not found: {resumes_dir}")
        return 0

    ids, documents, metadatas = [], [], []

    for md_file in sorted(resumes_path.rglob("main.md")):
        dir_name = md_file.parent.name
        stack, lang = _infer_stack_and_lang(dir_name)
        text = md_file.read_text(encoding="utf-8")
        chunks = _chunk_markdown(text, heading_pattern=r"^## ")

        for i, chunk in enumerate(chunks):
            doc_id = f"resume_{dir_name}_{i}"
            ids.append(doc_id)
            documents.append(chunk["text"])
            metadatas.append({
                "source": "resume",
                "stack": stack,
                "lang": lang,
                "section": chunk["section"],
                "source_file": str(md_file.relative_to(resumes_path)),
            })

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Indexed {len(ids)} resume chunks from {resumes_dir}")

    return len(ids)


def index_candidate_context(collection, candidate_context: str) -> int:
    """Chunk and index CANDIDATE_CONTEXT from config."""
    if not candidate_context.strip():
        return 0

    chunks = _chunk_markdown(candidate_context, heading_pattern=r"^### ")

    ids, documents, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        doc_id = f"candidate_ctx_{i}"
        ids.append(doc_id)
        documents.append(chunk["text"])
        metadatas.append({
            "source": "candidate_context",
            "stack": "general",
            "lang": "en",
            "section": chunk["section"],
        })

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Indexed {len(ids)} candidate context chunks")

    return len(ids)


def full_index(chromadb_dir: str, resumes_dir: str, candidate_context: str,
               model_name: str, hf_token: str = "", force: bool = False) -> int:
    """Full indexing pipeline: resumes + candidate context.

    Returns total chunks indexed. Skips if nothing changed (unless force=True).
    """
    if not force and not needs_reindex(chromadb_dir, resumes_dir, candidate_context):
        logger.info("Vector store up-to-date, skipping reindex")
        return 0

    collection = init_collection(chromadb_dir, model_name, hf_token)

    # Clear existing data for clean reindex
    try:
        existing = collection.count()
        if existing > 0:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
    except Exception:
        pass

    total = 0
    total += index_resumes(collection, resumes_dir)
    total += index_candidate_context(collection, candidate_context)

    _save_index_hash(chromadb_dir, resumes_dir, candidate_context)
    logger.info(f"Indexing complete: {total} total chunks")
    return total


# ── Querying ────────────────────────────────────────────────────────────────


def query_jobs(collection, job_text: str, n_results: int = 5) -> list[dict]:
    """Query the vector store with job text, return top chunks + distances.

    Returns list of dicts with keys: text, distance, metadata
    ChromaDB cosine distance: 0 = identical, 2 = opposite.
    We convert to similarity: 1 - (distance / 2), range [0, 1].
    """
    if not job_text.strip():
        return []

    results = collection.query(
        query_texts=[job_text],
        n_results=min(n_results, collection.count()),
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    chunks = []
    for doc, dist, meta in zip(
        results["documents"][0],
        results["distances"][0],
        results["metadatas"][0],
    ):
        similarity = 1 - (dist / 2)  # Convert cosine distance to similarity
        chunks.append({
            "text": doc,
            "similarity": round(similarity, 4),
            "distance": round(dist, 4),
            "metadata": meta,
        })

    return chunks
