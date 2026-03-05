"""Semantic job filtering using ChromaDB vector store + resume embeddings."""

import logging

logger = logging.getLogger(__name__)

_collection = None  # Lazy-initialized ChromaDB collection


def _ensure_index():
    """Lazy init: index resumes into ChromaDB if needed."""
    global _collection
    if _collection is not None:
        return _collection

    from .config import (
        CHROMADB_DIR, RESUMES_DIR, CANDIDATE_CONTEXT,
        SEMANTIC_MODEL_NAME, HF_API_TOKEN,
    )
    from .vectorstore import full_index, init_collection

    # Index (skips if up-to-date)
    full_index(
        chromadb_dir=CHROMADB_DIR,
        resumes_dir=RESUMES_DIR,
        candidate_context=CANDIDATE_CONTEXT,
        model_name=SEMANTIC_MODEL_NAME,
        hf_token=HF_API_TOKEN,
    )

    _collection = init_collection(CHROMADB_DIR, SEMANTIC_MODEL_NAME, HF_API_TOKEN)
    return _collection


def semantic_filter_jobs(jobs: list[dict], threshold: float = None) -> list[dict]:
    """Filter jobs by semantic similarity to resume/candidate context.

    For each job, queries the vector store with title + description.
    Attaches semantic_score, matched_stack, and relevant_chunks to each job.
    Filters out jobs below the threshold.

    Falls back to keyword-based pre_filter_jobs() if vector store is unavailable.
    """
    if threshold is None:
        from .config import SEMANTIC_THRESHOLD
        threshold = SEMANTIC_THRESHOLD

    try:
        collection = _ensure_index()
    except (ImportError, Exception) as e:
        logger.warning(f"Semantic filter unavailable ({e}), falling back to keyword filter")
        from .rank import pre_filter_jobs
        return pre_filter_jobs(jobs)

    if collection.count() == 0:
        logger.warning("Vector store empty, falling back to keyword filter")
        from .rank import pre_filter_jobs
        return pre_filter_jobs(jobs)

    from .vectorstore import query_jobs

    filtered = []
    for job in jobs:
        title = job.get("title") or ""
        desc = job.get("description") or ""
        query_text = f"{title}\n{desc}"

        chunks = query_jobs(collection, query_text, n_results=5)
        if not chunks:
            continue

        best_score = chunks[0]["similarity"]

        if best_score < threshold:
            continue

        # Determine dominant stack from top chunks
        stack_counts = {}
        for c in chunks:
            s = c["metadata"].get("stack", "general")
            stack_counts[s] = stack_counts.get(s, 0) + c["similarity"]
        matched_stack = max(stack_counts, key=stack_counts.get)

        # Attach semantic data to job
        job["semantic_score"] = best_score
        job["matched_stack"] = matched_stack
        job["relevant_chunks"] = chunks[:3]  # Top 3 for RAG context
        filtered.append(job)

    # Sort by semantic score descending
    filtered.sort(key=lambda j: j.get("semantic_score", 0), reverse=True)

    dropped = len(jobs) - len(filtered)
    logger.info(
        f"Semantic filter: kept {len(filtered)}/{len(jobs)} jobs "
        f"(threshold={threshold}, dropped {dropped})"
    )
    print(f"  Semantic filter: kept {len(filtered)}/{len(jobs)} jobs (threshold={threshold})")

    return filtered


def get_rag_context(job: dict) -> str:
    """Format retrieved resume chunks as RAG context for Claude prompt.

    Returns a string with the most relevant resume sections for the job.
    """
    chunks = job.get("relevant_chunks", [])
    if not chunks:
        return ""

    lines = [f"### Relevant Resume Context (stack: {job.get('matched_stack', 'general')})"]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("similarity", 0)
        lines.append(f"\n**Chunk {i}** (similarity={score:.2f}, source={source}, section={section}):")
        # Truncate very long chunks
        text = chunk.get("text", "")
        if len(text) > 500:
            text = text[:500] + "..."
        lines.append(text)

    return "\n".join(lines)
