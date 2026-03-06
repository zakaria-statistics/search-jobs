# Architecture

## Overview

A job search pipeline that automates scraping, uses semantic filtering to pre-screen jobs against resumes, then Claude to rank survivors by candidate fit, and provides a human-in-the-loop review before importing into an application tracker.

```
                        AUTOMATED PATH
                        ─────────────

  ┌──────────┐     ┌──────────┐     ┌───────────────────────────────┐     ┌──────────┐     ┌──────────┐
  │ scraper/ │ ──> │ output/  │ ──> │ ranker/                       │ ──> │ output/  │ ──> │ output/  │
  │          │     │ scraped_ │     │                               │     │filtered_ │     │ ranked_  │
  │ Indeed   │     │ *.json   │     │  ┌─────────────┐              │     │ *.json   │     │ *.json   │
  │ RemoteOK │     │          │     │  │ ChromaDB    │  Semantic    │     │          │     │          │
  │ Arbeitnow│     └──────────┘     │  │ (resumes)   │──filter──┐  │     └─────┬────┘     └─────┬────┘
  │ Rekrute  │                      │  └─────────────┘          │  │           │                │
  │ WTTJ     │                      │        ↑                  ↓  │           │                │
  └──────────┘     ┌──────────┐     │  ┌─────────────┐  ┌─────────┐│          │                v
                   │ resumes/ │ ──> │  │ vectorstore │  │ filter  ││          │         ┌──────────────┐
                   │ 8 resume │     │  │ .py (embed) │  │ (stage1)││          │         │  Claude AI   │
                   │ variants │     │  └─────────────┘  └─────────┘│          │         │  rank (stage2│
                   └──────────┘     │                              │          │         │  + RAG ctx)  │
                                    └──────────────────────────────┘          │         └──────┬───────┘
                                                                              │                │
                        MANUAL PATH                                           v                v
                        ───────────                                    ┌──────────────┐ ┌──────────────┐
  LinkedIn / APEC /                                                    │ pipeline.py  │ │ pipeline.py  │
  career pages     ─────────────────────────────────────────────────>  │ review       │ │ review       │
                      pipeline.py manual                               │ (human-in-   │ │              │
                                                                       │  the-loop)   │ │              │
                                                                       └──────┬───────┘ └──────┬───────┘
                                                                              │                │
                                                                              v                v
                                                                       ┌──────────────────────────────┐
                                                                       │ opportunity_tracker.py        │
                                                                       │ output/opportunities.json     │
                                                                       └──────────────────────────────┘
```

## Project Structure

```
job-search/
├── scraper/                     Job scrapers (one per source)
│   ├── base.py                    BaseScraper ABC — delay(), dedup()
│   ├── config.py                  Keywords, regions, per-source settings, match_job()
│   ├── models.py                  Job dataclass (title, company, location, url, ...)
│   ├── storage.py                 save_jobs() — timestamped JSON, dedup, merge
│   ├── indeed.py                  IndeedScraper — StealthyFetcher, multi-region
│   ├── remoteok.py                RemoteOKScraper — REST API
│   ├── arbeitnow.py               ArbeitnowScraper — REST API, location filtering
│   ├── rekrute.py                 RekruteScraper — Fetcher, Morocco-only
│   └── wttj.py                    WTTJScraper — Fetcher, Welcome to the Jungle
│
├── ranker/                      Semantic filtering + Claude-powered ranking
│   ├── config.py                  Candidate context, skill keywords, Claude & semantic settings
│   ├── prompts.py                 System prompt with scoring criteria, RAG instructions
│   ├── rank.py                    slim (+ RAG context) → Claude API → parse → save (accepts pre-filtered input)
│   ├── vectorstore.py             ChromaDB management: index resumes, query by job text
│   └── semantic_filter.py         Semantic pre-filter: embed jobs, compare to resume chunks
│
├── resumes/                     Resume variants (8 total, indexed into ChromaDB)
│   ├── ai_eng_.../main.md         AI/MLOps stack, English
│   ├── ai_fr_.../main.md          AI/MLOps stack, French
│   ├── aws_eng_.../main.md        AWS cloud stack, English
│   ├── aws_fr_.../main.md         AWS cloud stack, French
│   ├── az_eng_.../main.md         Azure cloud stack, English
│   ├── az_fr_.../main.md          Azure cloud stack, French
│   ├── devops_eng_.../main.md     DevOps stack, English
│   └── devops_fr_.../main.md      DevOps stack, French
│
├── scripts/                     CLI tools
│   ├── pipeline.py                Orchestrator: scrape | enrich | index | filter | rank | review | run | manual | status
│   ├── opportunity_tracker.py     Application tracking: add | list | update | stats | import | due
│   ├── contact_pipeline.py        Recruiter outreach: add | list | update | stats | due
│   └── job_search_queries.sh      Opens pre-built search URLs in browser
│
├── docs/                        Strategy & planning (static reference)
│   ├── 01_candidate_target.md     Profile, target roles, tech stack, positioning
│   ├── 02_company_goals.md        Hiring focus by sector (banking, telecom, retail, ESN)
│   ├── 03_opportunities_map.md    Platforms, company career URLs, search keywords
│   ├── 04_job_platforms.md        Tier-1/2/3 platform strategy, daily cadence
│   ├── 05_recruiter_contacts.md   Outreach templates, follow-up cadence, networking
│   └── 06_90_day_plan.md          12-week execution plan with KPIs
│
├── output/                      Generated data (gitignored)
│   ├── .chromadb/                 ChromaDB persistent vector store
│   ├── scraped_YYYY-MM-DD-HH-MM-SS.json   Timestamped scraped jobs
│   ├── filtered_YYYY-MM-DD-HH-MM-SS.json  Semantically filtered jobs
│   ├── ranked_YYYY-MM-DD-HH-MM-SS.json    Claude-ranked jobs
│   ├── opportunities.json         Application tracker state
│   └── contacts.json              Contact tracker state
│
├── ARCHITECTURE.md              This file
├── WORKFLOW.md                  Daily/weekly execution guide
├── WALKTHROUGH.md               Detailed execution examples & timelines
├── VECTORDB_BREAKDOWN.md        How the vector DB and embeddings work
├── requirements.txt             Python dependencies
└── .env                         ANTHROPIC_API_KEY (gitignored)
```

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
| `rank` | Claude ranking (auto-uses `filtered_*.json`, skips re-filtering), saves `output/ranked_*.json` |
| `review` | Interactive terminal — shows ranked jobs by priority, user approves/skips |
| `run` | Full chain: scrape → enrich → filter → rank → review |
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

## Data Formats

### scraped_YYYY-MM-DD-HH-MM-SS.json

```json
{
  "scraped_at": "2026-03-05T23:27:53",
  "total_jobs": 509,
  "jobs": [
    {
      "title": "DevOps Engineer",
      "company": "Sopra Steria",
      "location": "Paris, France",
      "url": "https://...",
      "source": "wttj",
      "date_posted": "2026-03-01",
      "description": "First 500 chars of job description...",
      "keyword": "DevOps Engineer",
      "region": "france",
      "scraped_at": "2026-03-05T23:27:53"
    }
  ]
}
```

### filtered_YYYY-MM-DD-HH-MM-SS.json

```json
{
  "filtered_at": "2026-03-05T23:30:00",
  "source_file": "output/scraped_2026-03-05-23-27-53.json",
  "total_input": 509,
  "total_filtered": 320,
  "jobs": [
    {
      "title": "DevOps Engineer",
      "company": "Sopra Steria",
      "location": "Paris, France",
      "url": "https://...",
      "source": "wttj",
      "description": "...",
      "semantic_score": 0.84,
      "matched_stack": "aws",
      "relevant_chunks": [
        {"text": "...", "similarity": 0.84, "metadata": {"stack": "aws", "section": "Professional Summary"}}
      ]
    }
  ]
}
```

### ranked_YYYY-MM-DD-HH-MM-SS.json

```json
{
  "search_summary": {
    "total_jobs_analyzed": 38,
    "average_fit_score": 62,
    "top_fit_score": 89,
    "score_distribution": {"excellent_80_plus": 4, "good_60_79": 12, "fair_40_59": 15, "poor_below_40": 7}
  },
  "ranked_jobs": [
    {
      "rank": 1,
      "title": "DevOps Engineer",
      "company": "Sopra Steria",
      "location": "Paris, France",
      "url": "https://...",
      "scores": {"skills_match": 85, "experience_fit": 90, "location_fit": 95, "growth_potential": 80, "overall": 87},
      "matching_skills": ["Kubernetes", "Terraform", "Azure", "CI/CD", "Docker"],
      "missing_skills": ["GCP"],
      "resume_tweaks": ["Emphasize AKS production experience"],
      "priority": "apply_now"
    }
  ],
  "global_insights": {
    "most_demanded_skills": ["Kubernetes", "Terraform", "AWS"],
    "skills_to_learn": ["GCP", "Datadog"],
    "market_observations": ["Strong demand for multi-cloud in France"],
    "recommended_search_refinements": ["Add 'Platform Engineer' keyword"]
  }
}
```

### opportunities.json

```json
{
  "next_id": 5,
  "opportunities": [
    {
      "id": 1,
      "company": "Sopra Steria",
      "role": "DevOps Engineer",
      "location": "Paris, France",
      "status": "Applied",
      "source": "scraper",
      "url": "https://...",
      "applied_date": "2026-03-02",
      "follow_up_date": "2026-03-07",
      "notes": "Score: 87/100 | Priority: apply_now | Skills: Kubernetes, Terraform, Azure",
      "history": [{"from": "New", "to": "Applied", "date": "2026-03-02T14:00:00"}]
    }
  ]
}
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `scrapling[all]` | HTML scraping (Fetcher for basic sites, StealthyFetcher for anti-bot) |
| `requests` | HTTP for REST API scrapers (RemoteOK, Arbeitnow) |
| `anthropic` | Claude API for job ranking |
| `python-dotenv` | Load ANTHROPIC_API_KEY from .env |
| `chromadb` | Persistent vector database for semantic resume search |
| `sentence-transformers` | Local embedding model (all-MiniLM-L6-v2, 384-dim) |

## Configuration

All tunable settings are in two config files:

**`scraper/config.py`** — search keywords, target regions, per-source rate limits and page limits, keyword matching patterns.

**`ranker/config.py`** — candidate profile context (skills, experience, target roles, location preferences), skill keywords for pre-filtering, Claude model and token settings, semantic filter settings (model, threshold, paths).

To change target roles, keywords, or regions: edit these two files. No other files need modification.

To update resumes: edit the `main.md` files under `resumes/`, then run `pipeline.py index --force` (or let the next `filter` auto-detect the change).
