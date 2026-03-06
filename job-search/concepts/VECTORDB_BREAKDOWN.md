# VectorDB & Embedding Breakdown

## What We Use

| Component | Tool | Purpose |
|-----------|------|---------|
| **Vector Database** | ChromaDB (persistent, on-disk) | Stores resume chunks as vectors, enables similarity search |
| **Embedding Model** | `all-MiniLM-L6-v2` (sentence-transformers) | Converts text into 384-dimensional vectors, runs locally |
| **Storage Location** | `output/.chromadb/` | On-disk persistent store, survives restarts |
| **Distance Metric** | Cosine similarity (HNSW index) | Measures how "close" two texts are in meaning (0-1 scale) |

## What Gets Indexed

Your resumes are split by `##` headings into chunks. Each chunk becomes a vector in the DB.

**Current state (69 chunks):**

| Source File | Stack | Lang | Chunks |
|-------------|-------|------|--------|
| `ai_eng_*/main.md` | ai | en | 7 |
| `ai_fr_*/main.md` | ai | fr | 7 |
| `aws_eng_*/main.md` | aws | en | 8 |
| `aws_fr_*/main.md` | aws | fr | 8 |
| `az_eng_*/main.md` | azure | en | 8 |
| `az_fr_*/main.md` | azure | fr | 8 |
| `devops_eng_*/main.md` | general* | en | 8 |
| `devops_fr_*/main.md` | general* | fr | 8 |
| `CANDIDATE_CONTEXT` (config.py) | general | en | 7 |
| **Total** | | | **69** |

> *Note: devops resumes are classified as `general` because `vectorstore.py:_infer_stack_and_lang()` only recognizes `ai`, `aws`, `az` as stack prefixes. The `devops` prefix falls through to the default. This means the semantic filter won't detect "devops" as a distinct matched_stack — it will work fine for similarity matching, but `job["matched_stack"]` won't say "devops".

## How Indexing Works (Step by Step)

```
pipeline.py index --force
         |
         v
1. HASH CHECK (vectorstore.py:needs_reindex)
   - MD5 hash all resumes/*/main.md + CANDIDATE_CONTEXT
   - Compare against stored hash in output/.chromadb/.index_hash
   - If same → skip (unless --force)
   - If different → proceed to reindex
         |
         v
2. LOAD EMBEDDING MODEL (vectorstore.py:_get_embedding_fn)
   - Try local sentence-transformers first (no API calls)
   - Fallback: HF Inference API (needs HF_API_TOKEN)
   - Fallback: raise error → pipeline falls back to keyword filter
         |
         v
3. INIT CHROMADB (vectorstore.py:init_collection)
   - Open persistent client at output/.chromadb/
   - Get or create collection "resumes" with cosine distance
   - Clear existing data for clean reindex
         |
         v
4. CHUNK RESUMES (vectorstore.py:_chunk_markdown)
   - For each resumes/*/main.md:
     - Split by "## " headings (Professional Summary, Technical Skills, etc.)
     - Each section becomes one chunk
     - Metadata attached: {stack, lang, section, source_file}
   - Stack/lang inferred from directory name:
     - ai_eng_* → stack=ai, lang=en
     - aws_fr_* → stack=aws, lang=fr
     - devops_eng_* → stack=general (not recognized)
         |
         v
5. CHUNK CANDIDATE CONTEXT (vectorstore.py:index_candidate_context)
   - Split CANDIDATE_CONTEXT from ranker/config.py by "### " headings
   - 7 chunks: Core Technical Skills, Differentiators, Certifications, etc.
   - Metadata: {source=candidate_context, stack=general}
         |
         v
6. EMBED & UPSERT
   - all-MiniLM-L6-v2 converts each text chunk → 384-dim float vector
   - Vectors + text + metadata upserted into ChromaDB
   - HNSW index built for fast approximate nearest-neighbor search
         |
         v
7. SAVE HASH
   - Write current hash to output/.chromadb/.index_hash
   - Next run skips if resumes haven't changed
```

## How Semantic Filtering Works (at Rank Time)

```
For each scraped job:

  "Senior DevOps Engineer - Kubernetes, Terraform, AWS"
         |
         v
  1. BUILD QUERY TEXT
     query = job.title + "\n" + job.description
         |
         v
  2. EMBED QUERY
     all-MiniLM-L6-v2 converts query → 384-dim vector
         |
         v
  3. SEARCH CHROMADB (top 5 nearest chunks)
     ChromaDB uses HNSW index to find 5 closest resume chunks
     Returns: [{text, distance, metadata}, ...]
         |
         v
  4. COMPUTE SIMILARITY
     similarity = 1 - (cosine_distance / 2)
     Range: 0.0 (unrelated) to 1.0 (identical meaning)
         |
         v
  5. THRESHOLD CHECK (default 0.65)
     best_similarity >= 0.65 → KEEP job
     best_similarity < 0.65  → DROP job
         |
         v
  6. DETERMINE MATCHED STACK
     Count which stack (ai/aws/azure/general) appears most in top chunks
     weighted by similarity score → matched_stack
         |
         v
  7. ATTACH RAG CONTEXT
     job["semantic_score"] = best_similarity
     job["matched_stack"] = "aws" (or ai/azure/general)
     job["relevant_chunks"] = top 3 chunks (text + metadata)
     These chunks are later sent to Claude as per-job context
```

**Example:**
```
Job: "Platform Engineer — Kubernetes, Terraform, AWS"
  → Query ChromaDB → top chunk: aws_eng resume "Professional Summary" (similarity=0.84)
  → 0.84 >= 0.65 → KEEP
  → matched_stack = "aws"
  → Claude sees this job WITH your AWS resume sections

Job: "Head Pastry Chef — French Cuisine"
  → Query ChromaDB → top chunk: some french resume "Langues" section (similarity=0.31)
  → 0.31 < 0.65 → DROP (never reaches Claude)
```

## What "Embedding" Means Concretely

The model `all-MiniLM-L6-v2` turns any text into a list of 384 numbers (a vector).

```
"Kubernetes cluster management with Terraform IaC"
    → [0.032, -0.118, 0.045, 0.201, ..., -0.089]  (384 floats)

"Managing container orchestration platforms using infrastructure automation"
    → [0.029, -0.112, 0.051, 0.198, ..., -0.091]  (384 floats)
    ^^ these two vectors are CLOSE (high cosine similarity)

"Baking croissants with French butter"
    → [-0.201, 0.089, -0.156, 0.012, ..., 0.178]  (384 floats)
    ^^ this vector is FAR from the first two
```

Texts with similar *meaning* (not just same words) produce similar vectors. This is why "container orchestration" matches Kubernetes experience even without the word "kubernetes".

## Fallback Chain

```
1. Local sentence-transformers (primary)
   ↓ ImportError or failure
2. HF Inference API (needs HF_API_TOKEN in .env)
   ↓ No token or API error
3. Keyword-based pre_filter_jobs() using 34 hardcoded terms from config.py
   (no vector DB, no embeddings — just string matching)
```

## Configuration (ranker/config.py)

| Setting | Value | Purpose |
|---------|-------|---------|
| `SEMANTIC_MODEL_NAME` | `all-MiniLM-L6-v2` | 22M param model, 384-dim embeddings |
| `SEMANTIC_THRESHOLD` | `0.65` | Minimum similarity to keep a job |
| `CHROMADB_DIR` | `output/.chromadb/` | Persistent vector store path |
| `RESUMES_DIR` | `resumes/` | Where resume markdown files live |
| `USE_SEMANTIC_FILTER` | `True` | Set False to skip vectors, use keyword filter |
