# Milestones

## Phase 1: Foundation -- Basic Scraping

| What | Detail |
|------|--------|
| Multi-source scraping | Indeed, RemoteOK, Arbeitnow, Rekrute, WTTJ |
| Keyword matching | 5-tier: title phrase, title word, tag phrase, tag strict, description lenient |
| Output | Timestamped JSON (`scraped_YYYY-MM-DD-HH-MM-SS.json`) with deduplication |
| Indeed multi-region | 9 country domains (MA, FR, DE, NL, BE, LU, PL, CH, UK) |
| Commit | `120b7af` .. `a7d4130` (2026-03-01 -- 2026-03-02) |

## Phase 2: AI Ranking -- Claude Integration

| What | Detail |
|------|--------|
| Claude API scoring | 4 dimensions: skills (40%), experience (30%), location (15%), growth (15%) |
| Priority labels | `apply_now`, `strong_match`, `worth_trying`, `long_shot`, `skip` |
| Job slimming | `slim_job()` strips heavy fields, `extract_skill_sentences()` for token efficiency |
| Keyword pre-filter | 34 skill terms in `CANDIDATE_SKILL_KEYWORDS` gate Claude calls |
| Commit | `d7f1228` (2026-03-01) |

## Phase 3: Semantic Intelligence -- Vector DB + RAG

| What | Detail |
|------|--------|
| ChromaDB vector store | Persistent at `output/.chromadb/`, cosine similarity space |
| Resume indexing | 8 variants (AI/AWS/Azure/DevOps x EN/FR) chunked by `##` headings |
| Semantic pre-filter | Cosine similarity threshold 0.65; runs locally, no API cost |
| RAG context | Matched resume chunks sent to Claude per-job |
| Stack-aware matching | Auto-detects best resume variant (ai/aws/azure/devops) per job |
| Change detection | MD5 hash-based auto-reindexing when resume files change |
| Commit | `79092ee` (2026-03-05) |

## Phase 4: Composite Scoring -- Multi-Signal Ranking

| What | Detail |
|------|--------|
| 5-dimension composite score | Replaces semantic-only sorting |
| Weights | semantic (0.35), skill_match (0.30), title_match (0.20), location_match (0.10), stack_depth (0.05) |
| Score buckets | top (0.75+), strong (0.60--0.75), moderate (0.45--0.60) |
| Score breakdown | Per-job breakdown showing why it ranked high or low |
| False positive reduction | Semantic-only high scores pushed down if poor title/skill match |
| Commit | `705ab8f` (2026-03-06) |

## Phase 5: Pipeline Maturity -- Tracking & Workflow

| What | Detail |
|------|--------|
| Indeed enrichment | Full description fetch with `extract_skill_sentences()` (top 50 jobs) |
| Application tracker | `opportunity_tracker.py` -- status flow, follow-up scheduling, import/export |
| Contact pipeline | `contact_pipeline.py` -- recruiter outreach with auto-cadence (Day 0/3/10) |
| Interactive review | `pipeline.py review` -- approve/skip/view per job, auto-imports to tracker |
| Pipeline status | `pipeline.py status` -- health check across all stages |
| Output organization | Timestamped run directories (`scraped_*`, `filtered_*`, `ranked_*`) |
| Commit | Incremental across `a7d4130` .. `705ab8f` |

## What's Next (ideas)

- Auto-application drafting (cover letter generation per job)
- Interview prep generation (company-specific question banks)
- Market trend analytics over time (skill demand, salary ranges)
- Resume auto-tailoring per job (adjust emphasis based on matched skills)
