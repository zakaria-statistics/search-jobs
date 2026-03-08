# Architecture

## Overview

A job search pipeline that automates scraping, uses semantic filtering to pre-screen jobs against resumes, then Claude to rank survivors by candidate fit, and provides a human-in-the-loop review before importing into an application tracker.

```
                        AUTOMATED PATH
                        ─────────────

  ┌──────────┐     ┌──────────┐     ┌───────────────────────────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │ scraper/ │ ──> │ output/  │ ──> │ ranker/                       │ ──> │ output/  │ ──> │ output/  │ ──> │ output/  │
  │          │     │ scraped  │     │                               │     │filtered_ │     │ prepared │     │ ranked   │
  │ Indeed   │     │ .json    │     │  ┌─────────────┐              │     │ *.json   │     │ .json    │     │ .json    │
  │ RemoteOK │     │          │     │  │ ChromaDB    │  Semantic    │     │          │     │          │     │          │
  │ Arbeitnow│     └──────────┘     │  │ (resumes)   │──filter──┐  │     └─────┬────┘     └─────┬────┘     └─────┬────┘
  │ Rekrute  │                      │  └─────────────┘          │  │           │                │                │
  │ WTTJ     │                      │        ↑                  ↓  │           │                │                │
  └──────────┘     ┌──────────┐     │  ┌─────────────┐  ┌─────────┐│          │                v                v
                   │ resumes/ │ ──> │  │ vectorstore │  │ filter  ││          │         ┌──────────────┐  ┌──────────────┐
                   │ 8 resume │     │  │ .py (embed) │  │ (stage1)││          │         │  prepare     │  │  Claude AI   │
                   │ variants │     │  └─────────────┘  └─────────┘│          │         │  slim_job()  │  │  rank (stage │
                   └──────────┘     │                              │          │         │  + RAG ctx   │  │  3) batched  │
                                    └──────────────────────────────┘          │         │  (INSPECT)   │  │  streaming   │
                                                                              │         └──────┬───────┘  └──────┬───────┘
                                                                              │                │                │
                        MANUAL PATH                                           v                v                v
                        ───────────                                    ┌──────────────┐ ┌──────────────────────────────┐
  LinkedIn / APEC /                                                    │ pipeline.py  │ │ pipeline.py                  │
  career pages     ─────────────────────────────────────────────────>  │ review       │ │ review                       │
                      pipeline.py manual                               │ (human-in-   │ │                              │
                                                                       │  the-loop)   │ │                              │
                                                                       └──────┬───────┘ └──────────────┬───────────────┘
                                                                              │                        │
                                                                              v                        v
                                                                       ┌──────────────────────────────────────┐
                                                                       │ opportunity_tracker.py                │
                                                                       │ output/opportunities.json             │
                                                                       └──────────────────────────────────────┘
```

## Project Structure

See [README.md](README.md#project-structure) for the full project tree.

## Modules

### scraper/

Collects raw job listings from five sources. Each scraper inherits from `BaseScraper` and implements `scrape(keywords, regions, max_pages) -> list[Job]`.

| Source | Type | Coverage | Anti-bot |
|--------|------|----------|----------|
| Indeed | HTML scraping | 9 country domains (FR, DE, NL, BE, ...) | StealthyFetcher (headless) |
| RemoteOK | REST API | Remote-only jobs globally | None needed |
| Arbeitnow | REST API | Europe-focused, remote-friendly | None needed |
| Rekrute | HTML scraping | Morocco only | Fetcher |
| WTTJ | HTML scraping | France-focused, startup-heavy | Fetcher |

**Keyword matching** (`config.py:match_job`): 4-tier strategy — full phrase in title, role terms in title, full phrase in tags, strict terms in tags. Avoids false positives like "sre" inside unrelated German words.

**Storage** (`storage.py`): Saves to `scraped_YYYY-MM-DD-HH-MM-SS.json`. Each scrape run creates a separate timestamped file.

### ranker/

Scores and ranks scraped jobs using a two-stage pipeline: semantic pre-filtering via ChromaDB (standalone step), then Claude-based scoring with RAG context.

```
Overall = (Skills Match x 0.40) + (Experience Fit x 0.30)
        + (Location Fit x 0.15) + (Growth Potential x 0.15)
```

**Stage 1 — Semantic Filter** (`pipeline.py filter` → `semantic_filter.py` + `vectorstore.py`):

A standalone pipeline step that runs without any Claude API call:

1. **Index** — 8 resume variants + `CANDIDATE_CONTEXT` chunked by headings, embedded with `all-MiniLM-L6-v2`, stored in ChromaDB (`output/.chromadb/`)
2. **Query** — each job's `title + description` is embedded and compared to resume chunks via cosine similarity
3. **Filter** — jobs below the similarity threshold (0.65) are dropped
4. **Enrich** — surviving jobs get `semantic_score`, `matched_stack` (ai/aws/azure), and top 3 `relevant_chunks` attached
5. **Save** — writes `filtered_YYYY-MM-DD-HH-MM-SS.json` with full breakdown

**Stage 2 — Claude Ranking** (`pipeline.py rank` → `rank.py`):

Automatically detects and uses the latest `filtered_*.json`, skipping re-filtering:

1. **Slim** — keeps ranking-relevant fields, attaches matched resume chunks as RAG context
2. **Claude API** — sends slimmed jobs + per-job resume context, receives scored JSON
3. **Save** — writes `ranked_YYYY-MM-DD-HH-MM-SS.json`

**Fallback**: if ChromaDB/sentence-transformers unavailable, falls back to keyword-based `pre_filter_jobs()` (34 terms).

**Output per job**: rank, scores (4 dimensions + overall), matching skills, missing skills, resume tweaks, priority label, semantic_score, matched_stack.

**Global insights**: most demanded skills, skills to learn, market observations, search refinements.

### vectorstore.py — How Indexing Works

```
resumes/ai_eng_*/main.md    ──┐
resumes/aws_eng_*/main.md   ──┤
resumes/az_eng_*/main.md    ──┤ chunk by ## headings ──> embed ──> ChromaDB
resumes/devops_eng_*/main.md──┤                                   (cosine space)
resumes/*_fr_*/main.md      ──┤   metadata: {stack, lang, section}
CANDIDATE_CONTEXT           ──┘ chunk by ### headings
```

- ~69 total chunks indexed (62 resume + 7 candidate context)
- Hash-based change detection: reindexes only when files change
- Embedding model: `all-MiniLM-L6-v2` (384-dim, ~22M params, runs locally)

### semantic_filter.py — How Filtering Works

```
job.title + job.description
    ↓ embed
    ↓ query ChromaDB (top 5 chunks)
    ↓ best_similarity >= 0.65 → KEEP (attach score + stack + chunks)
    ↓ best_similarity < 0.65  → DROP
```

Stack detection: the dominant stack across top chunks determines `matched_stack`. This tells Claude which resume variant (AI/AWS/Azure/DevOps) is most relevant for that job.

### scripts/pipeline.py

Unified CLI that chains everything:

| Command | What it does |
|---------|-------------|
| `scrape` | Runs selected scrapers, saves to `output/scraped_*.json` |
| `enrich` | Fetches full Indeed job descriptions for top 50 jobs |
| `index` | Indexes resumes into ChromaDB (auto-runs on first `filter`) |
| `filter` | Semantic pre-filter only, saves `output/filtered_*.json` with breakdown |
| `validate` | Check job URLs for closed/expired postings, saves `validated.json` + `closed.json` |
| `rank` | Claude ranking (auto-uses `prepared.json`), saves `output/ranked_*.json` |
| `review` | Interactive terminal — shows ranked jobs by priority, user approves/skips, `[c]heck url` |
| `run` | Full chain: scrape → enrich → filter → validate → prepare → rank → review |
| `manual` | Delegates to `opportunity_tracker.py add` for manual entry |
| `status` | Counts across pipeline stages (scraped, filtered, ranked, tracked, by status) |

The `filter` command is the inspection point — you see what passes, check scores and stack distribution, then decide to send to Claude via `rank`.

The `review` command is the human-in-the-loop step. Approved jobs are written directly into `output/opportunities.json` with score and skills metadata.

### scripts/opportunity_tracker.py

Tracks all job applications regardless of source (automated or manual). Status flow:

```
New → Applied → Screening → Interview → Technical → Offer → Accepted
                                                          → Rejected
                                                  → Withdrawn
```

Auto-sets follow-up date 5 days after applying. The `import` subcommand bulk-imports from ranked JSON files, deduplicating by URL.

### scripts/contact_pipeline.py

Tracks recruiter and tech lead outreach with automated follow-up cadence (Day 0 → Day 3 → Day 7 → Day 21 pause).

## Pipeline Data Flow — Stage by Stage

Read sequentially. Each stage's output becomes the next stage's input. Fields added at each stage are marked with `[+NEW]`.

---

### Stage 1: Scrape — External Calls and Raw Output

**What happens:** 6 scrapers call external sources, normalize responses into `Job` dataclass, deduplicate by URL.

**External calls per source:**

| Source | Call | Request | Response (relevant fields) |
|--------|------|---------|---------------------------|
| Indeed | `StealthyFetcher.fetch(url, headless=True)` | GET `https://{domain}/jobs?q={keyword}&l={location}&start={page*10}` | HTML → parse `.job_seen_beacon` cards → title, company, location, snippet |
| RemoteOK | `requests.get(REMOTEOK_API_URL)` | GET `https://remoteok.com/api` | JSON array: `{position, company, location, tags[], description, date, slug}` |
| Arbeitnow | `requests.get(ARBEITNOW_API_URL, params={page})` | GET `https://www.arbeitnow.com/api/job-board-api?page=N` | JSON: `{data: [{title, company_name, location, tags[], description, url, remote, created_at}]}` |
| WTTJ | `requests.post(ALGOLIA_URL, json={query, page, hitsPerPage})` | POST Algolia search index | JSON: `{hits: [{name, organization{name,slug}, profile, office{city,country_code}, remote, salary_*, contract_type, sectors[], slug}]}` |
| Rekrute | `Fetcher.fetch(url)` | GET `https://www.rekrute.com/...` | HTML → parse job cards |
| LinkedIn | `requests.get(url, proxies=dataimpulse)` | GET `linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=...&location=...&start=N` | HTML fragments → parse `.base-search-card` divs → title, company, location, date, URL |

**Schema transformation:** Each source maps differently into the `Job` dataclass:

```
RemoteOK.position     → Job.title          Indeed card h2.jobTitle  → Job.title
RemoteOK.company      → Job.company        Indeed [data-testid]    → Job.company
RemoteOK.tags[]       → used for matching   WTTJ.organization.name → Job.company
RemoteOK.description  → Job.description[:500]
```

**Output:** `output/runs/{ts}/scraped.json`

```json
{
  "scraped_at": "2026-03-06T15:20:10",
  "total_jobs": 509,
  "jobs": [{
    "title":       "DevOps Engineer",        // from source
    "company":     "Sopra Steria",           // from source
    "location":    "Paris, France",          // from source, normalized
    "url":         "https://...",            // built from source slugs/hrefs
    "source":      "wttj",                   // which scraper
    "date_posted": "2026-03-01",             // from source or ""
    "description": "First 500 chars...",     // truncated, raw
    "keyword":     "DevOps Engineer",        // which search keyword matched
    "region":      "france",                 // detected from location
    "scraped_at":  "2026-03-06T15:20:10"     // when scraped
  }]
}
```

**10 fields per job.** This is the base schema — all downstream stages build on it.

---

### Stage 2: Enrich — Indeed Full Descriptions

**What happens:** Fetches full job pages for Indeed jobs with short descriptions (<100 chars). Extracts skill-relevant sentences using NLP-lite heuristics.

**External call:**
```
StealthyFetcher.fetch(job.url, headless=True)
  → parse #jobDescriptionText
  → extract_skill_sentences(html) → keeps only lines containing skill keywords
  → job["description"] = skill_text  (in-place mutation)
```

**Schema drift:** No new fields. `description` field gets **replaced** (was snippet → now skill-relevant sentences, up to 800 chars).

**Input:** `scraped.json` (same file, mutated in-place before saving)
**Output:** Same `scraped.json` with enriched descriptions for Indeed jobs

---

### Stage 3: Filter — Semantic Matching + Composite Scoring

**What happens:** Each job is embedded and compared to resume chunks in ChromaDB. Five scoring signals are computed. Jobs below threshold are dropped. Survivors are bucketed by score.

**Internal calls (no external API):**

```
For each job:
  1. query_text = job.title + "\n" + job.description
  2. ChromaDB query(query_text, n_results=5)
     → returns [{text, distance, metadata{stack, lang, section, source}}]
     → similarity = 1 - (distance / 2)
  3. If best_similarity < 0.65 → DROP job
  4. Else → compute_composite_score(job):
     → semantic:       best_similarity (from ChromaDB)
     → skill_match:    count(CANDIDATE_SKILL_KEYWORDS in job text) / 8, capped at 1.0
     → title_match:    count(TARGET_TITLE_PATTERNS regex in title) / 2, capped at 1.0
     → location_match: 1.0 if TARGET_LOCATIONS in location, 0.8 if "remote" in desc, else 0.0
     → stack_depth:    chunk stack agreement ratio × bonus for specific stack
     → composite = Σ(weight × signal)
```

**Schema drift — 5 fields added per job:**

```json
{
  // ... all 10 base fields from Stage 1 ...
  "semantic_score":  0.84,                    // [+NEW] best cosine similarity
  "matched_stack":   "aws",                   // [+NEW] dominant resume stack
  "relevant_chunks": [                        // [+NEW] top 3 resume chunks (RAG context)
    {
      "text": "Professional Summary: 5+ years DevOps...",
      "similarity": 0.84,
      "metadata": {"stack": "aws", "lang": "en", "section": "Professional Summary", "source": "aws_eng_*/main.md"}
    }
  ],
  "composite_score": 0.7823,                  // [+NEW] weighted multi-signal score
  "score_breakdown": {                         // [+NEW] per-signal scores
    "semantic": 0.84,
    "skill_match": 0.875,
    "title_match": 1.0,
    "location_match": 1.0,
    "stack_depth": 0.8
  }
}
```

**Output:** 3 bucket files in `output/runs/{ts}/`:

| File | Score Range | Purpose |
|------|-------------|---------|
| `filtered_top.json` | 0.75 -- 1.0 | Send to Claude first |
| `filtered_strong.json` | 0.60 -- 0.75 | Rank if top bucket is thin |
| `filtered_moderate.json` | 0.45 -- 0.60 | Rank as last resort |

Each file wraps jobs in metadata:
```json
{
  "filtered_at": "2026-03-06T15:20:15",
  "source_file": "output/runs/2026-03-06-15-20-10/scraped.json",
  "bucket": "top",
  "score_range": "0.75-1.01",
  "total_input": 509,
  "total_in_bucket": 67,
  "jobs": [/* 15-field job objects sorted by composite_score desc */]
}
```

**15 fields per job** (10 base + 5 added).

---

### Stage 4: Validate — URL Liveness Check (no API call)

**What happens:** Each job's URL is checked for liveness. Closed/expired postings are dropped before spending Claude API tokens. Uses per-source detection patterns.

**Detection logic (sequential):**
1. HTTP status: 404 → `not_found`, 410 → `closed`, 4xx → `error`
2. Redirect check: final URL contains `/jobs?`, `/expired`, etc. when original didn't
3. Page content: regex match against first 5K chars (per-source patterns)
4. No match → `live` (conservative default)

**Per-source configuration:**

| Source | Fetcher | Closed patterns |
|--------|---------|----------------|
| indeed | StealthyFetcher | "this job has expired", "cette offre.*n'est plus disponible" |
| wttj | requests | "cette offre n'est plus disponible", "offre expirée" |
| remoteok | requests | "this job is no longer available", "position has been filled" |
| arbeitnow | requests | "job not found", "position is no longer available" |
| rekrute | StealthyFetcher | "offre expirée", "offre clôturée" |

**Schema drift — 3 fields added per job:**

```json
{
  // ... all fields from previous stage ...
  "url_status":      "live",                    // [+NEW] live|closed|not_found|error
  "url_status_code": 200,                       // [+NEW] HTTP status code
  "url_checked_at":  "2026-03-07T10:30:00"      // [+NEW] when checked
}
```

**Output:** 2 files in `output/runs/{ts}/`:

| File | Content |
|------|---------|
| `validated.json` | Live jobs (passed validation) |
| `closed.json` | Dropped jobs (reference) |

Each file wraps jobs in metadata:
```json
{
  "validated_at": "2026-03-07T10:30:00",
  "source_file": "output/runs/.../filtered_top.json",
  "total_input": 67,
  "total_live": 58,
  "total_closed": 9,
  "jobs": [/* job objects with url_status fields */]
}
```

**Rate limiting:** 3-6 second random delay between requests, grouped by source, max 200 URLs per run.

---

### Stage 5: Prepare — Slim for Claude (no API call)

**What happens:** Filtered jobs are slimmed into exactly what Claude will receive. Saved as `prepared.json` for inspection before spending API tokens.

**Transformation — `slim_job()` per job:**

```
15-field filtered job → ~12-field slim job (for token efficiency)

Kept:    title, company, location, url, source, date_posted, keyword, region
Changed: description → extract_skill_sentences() if > 600 chars
Added:   resume_context (formatted RAG text from relevant_chunks)
         semantic_score (float, passed through)
         matched_stack (string, passed through)
Dropped: relevant_chunks (raw array), composite_score, score_breakdown
```

**Output:** `output/runs/{ts}/prepared.json`

```json
{
  "prepared_at": "2026-03-06T15:25:00",
  "source_file": "output/runs/2026-03-06-15-20-10/filtered_top.json",
  "total_jobs": 67,
  "jobs": [/* slim job objects — this IS the Claude payload */]
}
```

**Terminal output includes:** job count, payload size in chars, token estimate, fields per job, RAG context coverage, top 5 preview.

---

### Stage 6: Rank — Claude API Call

**What happens:** Prepared jobs are sent to Claude. Claude returns scored + ranked JSON.

**How Claude knows the candidate profile:**

Claude receives two things — the candidate profile as the **system prompt**, and the jobs as the **user message**. They come from different places:

```
ranker/config.py
  └── CANDIDATE_CONTEXT (string) ─── your skills, experience, target roles, locations, differentiators
        ↓ imported by
ranker/prompts.py
  └── SYSTEM_PROMPT_JOBS = f"...{CANDIDATE_CONTEXT}..." ─── full system prompt with scoring criteria
        ↓ sent as system message
rank_jobs()
  └── client.messages.create(
         system=SYSTEM_PROMPT_JOBS,    ←── candidate profile + scoring rules
         messages=[{user: jobs_json}]  ←── prepared jobs (from prepared.json)
       )
```

The candidate profile is **not** in `prepared.json` — it's sent separately as the system prompt. `prepared.json` contains only the job data. To update what Claude knows about you, edit `CANDIDATE_CONTEXT` in `ranker/config.py`.

**External call — Anthropic API (streaming, batched):**

Jobs are auto-split into batches of 30 (`BATCH_SIZE` in `rank.py`) to stay within output token limits. Each batch is a separate streamed API call:

```
For each batch of ~30 jobs:
  POST https://api.anthropic.com/v1/messages (streamed)
  {
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 16384,
    "stream": true,
    "system": SYSTEM_PROMPT_JOBS,
    "messages": [{"role": "user", "content": "Analyze and rank the following 30 job postings...\n\n{batch_json}"}]
  }
```

**Batching and merge flow:**
```
67 jobs → split into 3 batches (30 + 30 + 7)
  ↓
_call_claude(batch 1) → {ranked_jobs: [...], global_insights: {...}}
_call_claude(batch 2) → {ranked_jobs: [...], global_insights: {...}}
_call_claude(batch 3) → {ranked_jobs: [...], global_insights: {...}}
  ↓
_merge_results() → combine ranked_jobs, re-sort by overall score,
                   re-number ranks 1..N, deduplicate insights
  ↓
ranked.json (single merged output, same schema as single-batch)
```

**Progress feedback during streaming:**
```
  Analyzing 67 jobs with claude-sonnet-4-5-20250929...
  Split into 3 batches of ~30 jobs each
  [1/3] Sending 30 jobs (~20,000 tokens in, 16,384 max out)
  [1/3] Streaming response...
  [1/3] Receiving... 5,000 tokens (~60s)
  [1/3] Done in 85.0s (35000 in / 8500 out)
  [2/3] Sending 30 jobs (...)
  ...
  Merging 3 batch results and re-ranking globally...
  Total time: 210.5s for 67 jobs
```

**Truncation safety:** Each batch of 30 needs ~7500 output tokens, well within the 16384 limit. If a batch still truncates, it's skipped with a warning and the remaining batches continue. Rule of thumb: ~250 output tokens per job.

**What Claude receives per job (slim schema):**
```json
{
  "title": "DevOps Engineer",
  "company": "Sopra Steria",
  "location": "Paris, France",
  "url": "https://...",
  "source": "wttj",
  "date_posted": "2026-03-01",
  "description": "Skill-relevant sentences...",
  "keyword": "DevOps Engineer",
  "region": "france",
  "semantic_score": 0.84,
  "matched_stack": "aws",
  "resume_context": "### Relevant Resume Context (stack: aws)\n\n**Chunk 1** (similarity=0.84):\n5+ years DevOps..."
}
```

**What Claude returns (completely new schema):**

```json
{
  "search_summary": {
    "total_jobs_analyzed": 67,
    "average_fit_score": 62,
    "top_fit_score": 89,
    "score_distribution": {
      "excellent_80_plus": 4,
      "good_60_79": 12,
      "fair_40_59": 15,
      "poor_below_40": 7
    }
  },
  "ranked_jobs": [{
    "rank":            1,                                      // [+NEW] Claude's ranking
    "title":           "DevOps Engineer",                      // passed through
    "company":         "Sopra Steria",                         // passed through
    "location":        "Paris, France",                        // passed through
    "url":             "https://...",                           // passed through
    "scores": {                                                // [+NEW] Claude's 4-dimension scoring
      "skills_match":    85,                                   //   0-100
      "experience_fit":  90,                                   //   0-100
      "location_fit":    95,                                   //   0-100
      "growth_potential": 80,                                  //   0-100
      "overall":         87                                    //   weighted average
    },
    "matching_skills": ["Kubernetes", "Terraform", "Azure"],   // [+NEW] what matched
    "missing_skills":  ["GCP"],                                // [+NEW] what's missing
    "resume_tweaks":   ["Emphasize AKS production experience"],// [+NEW] actionable advice
    "priority":        "apply_now"                             // [+NEW] apply_now|strong_match|worth_trying|long_shot|skip
  }],
  "global_insights": {                                         // [+NEW] cross-job analysis
    "most_demanded_skills": ["Kubernetes", "Terraform", "AWS"],
    "skills_to_learn": ["GCP", "Datadog"],
    "market_observations": ["Strong demand for multi-cloud in France"],
    "recommended_search_refinements": ["Add 'Platform Engineer' keyword"]
  }
}
```

**Output:** `output/runs/{ts}/ranked.json`

**Schema is completely replaced.** Claude's output has its own structure — the 15-field filtered job is gone, replaced by Claude's 9-field ranked job + global insights.

---

### Stage 7: Review — Human Approval → Tracker

**What happens:** User reviews ranked jobs interactively. Approved jobs are written to `opportunities.json`.

**Schema transformation — ranked job → opportunity:**

```
ranked_job.title    → opportunity.role
ranked_job.company  → opportunity.company
ranked_job.location → opportunity.location
ranked_job.url      → opportunity.url
ranked_job.scores   → opportunity.notes (formatted as "Score: 87/100 | Priority: apply_now | Skills: ...")
(source = "scraper") → opportunity.source
(status = "New")    → opportunity.status
```

**Output:** `output/opportunities.json` (persistent, accumulates across runs)

```json
{
  "next_id": 5,
  "opportunities": [{
    "id":              1,
    "company":         "Sopra Steria",
    "role":            "DevOps Engineer",
    "location":        "Paris, France",
    "status":          "New",                    // → Applied → Screening → Interview → ...
    "source":          "scraper",
    "url":             "https://...",
    "applied_date":    null,                     // set when status → Applied
    "follow_up_date":  null,                     // auto-set 5 days after applied
    "notes":           "Score: 87/100 | Priority: apply_now",
    "history":         []                        // [{from, to, date}] on each status change
  }]
}
```

---

### Full Schema Drift Summary

```
Stage 1 (scrape):    10 fields  → base Job schema
Stage 2 (enrich):    10 fields  → description replaced in-place (no new fields)
Stage 3 (filter):    15 fields  → +semantic_score, +matched_stack, +relevant_chunks, +composite_score, +score_breakdown
Stage 4 (validate):  18 fields  → +url_status, +url_status_code, +url_checked_at (closed jobs dropped)
Stage 5 (prepare):  ~12 fields → slim_job() drops chunks/scores, adds resume_context (INSPECTABLE)
Stage 6 (rank):     NEW SCHEMA → Claude returns rank, scores{4}, matching_skills, missing_skills, resume_tweaks, priority
Stage 7 (review):   NEW SCHEMA → opportunity with id, status, dates, history (persistent tracker)
```

```
                    ┌─────────────────────────────────────────────┐
  scrape            │ title company location url source           │
  10 fields         │ date_posted description keyword region      │
                    │ scraped_at                                  │
                    └──────────────────┬──────────────────────────┘
                                       │ enrich (description replaced)
                    ┌──────────────────▼──────────────────────────┐
  filter            │ ... all 10 base fields ...                  │
  +5 fields = 15    │ +semantic_score  +matched_stack             │
                    │ +relevant_chunks +composite_score           │
                    │ +score_breakdown                            │
                    └──────────────────┬──────────────────────────┘
                                       │ validate: check URL liveness
                    ┌──────────────────▼──────────────────────────┐
  validate          │ ... all 15 filtered fields ...              │
  +3 fields = 18    │ +url_status  +url_status_code               │
  (closed dropped)  │ +url_checked_at                             │
                    └──────────────────┬──────────────────────────┘
                                       │ prepare: slim_job() strips to ~12 fields
                    ┌──────────────────▼──────────────────────────┐
  prepared.json     │ title company location url source ...       │
  ~12 fields        │ description (skill-extracted)               │
  (INSPECT HERE)    │ +resume_context (formatted RAG text)        │
                    │ semantic_score, matched_stack                │
                    └──────────────────┬──────────────────────────┘
                                       │ rank: sends to Claude API
                    ┌──────────────────▼──────────────────────────┐
  Claude API        │ receives: COMPLETELY NEW schema             │
  output            │ rank, scores{4+overall}, matching_skills,   │
                    │ missing_skills, resume_tweaks, priority     │
                    └──────────────────┬──────────────────────────┘
                                       │ user approves
                    ┌──────────────────▼──────────────────────────┐
  opportunities     │ ANOTHER NEW schema (tracker)                │
  persistent DB     │ id, role, company, status, dates, history   │
                    └─────────────────────────────────────────────┘
```
