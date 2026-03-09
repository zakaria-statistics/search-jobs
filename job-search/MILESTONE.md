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
| Output organization | Timestamped run dirs (`output/runs/{ts}/`) with `latest` symlink |
| Prepare stage | Externalized `slim_job()` — inspect `prepared.json` before API call |
| Batched ranking | Auto-splits into batches of 30, streams with progress, merges globally |
| Docs consolidation | GUIDE.md, MILESTONE.md, CLAUDE.md; trimmed README/ARCHITECTURE |
| Relevance indicator | `ranker/relevance.py` — per-stage summary block (source/keyword/score breakdowns) injected into every JSON output |
| Google Drive sync | `pipeline.py sync` — rclone-based sync of latest run + persistent files to Google Drive |
| Commit | `fbf10f5` (2026-03-06), `c7472a8` (relevance), `TBD` (sync) |

## Phase 6: URL Validation -- Dead Posting Detection

| What | Detail |
|------|--------|
| URL liveness checking | New `scraper/url_validator.py` module detects closed/expired job postings |
| Per-source detection | Pattern-based detection for Indeed, WTTJ, RemoteOK, Arbeitnow, Rekrute |
| Detection logic | HTTP status (404/410) → redirect signals → page content regex → default live |
| New pipeline stage | `validate` between filter and prepare (step 4/7) |
| Output artifacts | `validated.json` (live jobs) + `closed.json` (dropped) per run |
| Review integration | `[c]heck url` option in interactive review for quick re-check |
| Optional stage | `--skip-validate` flag on `run` command to bypass |
| Rate limiting | Grouped by source, random delay (3-6s), max 200 URLs per run |
| Commit | `d158c91` (2026-03-07) |

## Phase 7: LinkedIn Scraper -- Proxy-Powered Source Expansion

| What | Detail |
|------|--------|
| LinkedIn scraper | New `scraper/linkedin.py` — 6th source via LinkedIn public guest API |
| DataImpulse proxy | Residential proxy integration (`.env` credentials, no account risk) |
| Byte budget | Per-run cap (`LINKEDIN_MAX_BYTES_PER_RUN = 10 MB`) to protect 5GB/month plan |
| Cost tracking | Logs requests, MB transferred, and estimated proxy cost per run |
| Rate limiting | 4-8s random delay between requests + 429 detection auto-stops |
| Region support | 9 regions matching existing Indeed config (MA, FR, DE, NL, BE, LU, PL, CH, UK) |
| Pipeline integration | `--sources linkedin` flag, included in full `run` command |
| dotenv loading | `pipeline.py` now loads `.env` at startup for all env-dependent modules |
| Commit | `f69d634` (2026-03-08) |

## Phase 8: Offer Intelligence -- Ghost Detection & Prediction Model (PLANNED)

| What | Detail |
|------|--------|
| SQLite intelligence DB | `output/intelligence.db` — persistent cross-run knowledge store (offers, runs, sightings, company reviews, careers page cache) |
| History recorder | Auto-records every scraped job with fingerprint tracking; backfills 5 existing runs (642 jobs, 99 cross-run overlaps) |
| Ghost prediction model | 9-signal weighted scorer: posting age, repost frequency, employer type, description quality, company intel, pipeline language, careers page match, description hash, contact present |
| Model progression | Weighted heuristic (day 1) → Bayesian updates (~20 outcomes) → Logistic Regression (~100) → GBDT (~500) |
| Blocker detection | Regex extraction for visa, language, clearance, seniority blockers with hard/soft/uncertain severity |
| Time-risk scoring | Effort estimation (easy apply vs take-home vs multi-round) × late-rejection probability → QUICK WIN / WORTH INVESTING / LOTTERY TICKET / TIME TRAP |
| Action tiers | Combines ghost score + blockers + fit + time-risk into actionable terminal report |
| Glassdoor scraper | Company review intelligence (ratings, interview difficulty, salary data) via DataImpulse proxy, cached in SQLite |
| Careers page checker | HTTP check if job exists on company's own site (ghost signal) |
| Description length | Scraper cap raised from 500 → 3000 chars for better signal extraction |
| Feedback loop | Application outcomes (response/ghosted/rejected/interview) feed back into model weights via Bayesian updates |
| Research backing | Based on 2025–2026 ghost job studies: 18–27% of listings are ghosts (Greenhouse, ResumeUp.AI, Clarify Capital) |
| New pipeline stage | `analyze` between validate and prepare |
| Commit | `TBD` |

## What's Next (ideas)

- Cover letter generation per job (Claude API, run on Tier 1/2 only)
- Success predictor model (P(response) per job, LogReg → LightGBM)
- Market intelligence (skill demand trends, salary clustering, timing optimization)
- Resume auto-tailoring per job (adjust emphasis based on matched skills)
- Company targeting (proactive: watch companies that hire your profile regularly)
