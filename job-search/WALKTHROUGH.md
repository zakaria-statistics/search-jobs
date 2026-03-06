# Pipeline Walkthrough — Timelines, Execution & Examples

This document walks through every execution path with concrete input/output examples, timelines, and terminal output so you can understand exactly what happens at each stage.

---

## Table of Contents

0. [Python Environment Setup](#0-python-environment-setup)
1. [Full Pipeline Run](#1-full-pipeline-run)
2. [Scrape Only — All Sources](#2-scrape-only--all-sources)
3. [Scrape Only — API Sources (Fast)](#3-scrape-only--api-sources-fast)
4. [Scrape with Custom Keywords & Regions](#4-scrape-with-custom-keywords--regions)
5. [Index Resumes (Semantic Setup)](#5-index-resumes-semantic-setup)
6. [Semantic Filter (Standalone)](#6-semantic-filter-standalone)
7. [Rank (Claude AI Scoring)](#7-rank-claude-ai-scoring)
8. [Interactive Review](#8-interactive-review)
9. [Application Tracking](#9-application-tracking)
10. [Contact Pipeline](#10-contact-pipeline)
11. [Pipeline Status Check](#11-pipeline-status-check)
12. [Manual Search URLs](#12-manual-search-urls)

---

## 0. Python Environment Setup

Before running any command, set up and activate the virtual environment:

```bash
cd job-search
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Index resumes into ChromaDB (one-time, ~3 seconds)
python scripts/pipeline.py index
```

For every new terminal session, re-activate:

```bash
cd job-search
source .venv/bin/activate
```

---

## 1. Full Pipeline Run

**Command:**
```bash
python scripts/pipeline.py run
```

**Timeline:**
```
00:00  Start
00:00  [1/5] SCRAPING — launches all 5 scrapers sequentially
00:10  Indeed finishes (9 domains x 8 keywords x 3 pages, headless browser) — ~1000 jobs
00:45  RemoteOK finishes (REST API, lenient matching) — ~45 jobs
01:15  Arbeitnow finishes (REST API, 15 pages, lenient matching) — ~70 jobs
01:30  Rekrute finishes (Morocco only) — ~10 jobs
03:30  WTTJ finishes (Algolia API, 8 keywords x 3 pages) — ~400 jobs
03:30  Scraped file saved: output/scraped_2026-03-05-10-30-00.json
03:30  [2/5] ENRICHING — fetches full Indeed job descriptions
03:30  Picks top 50 Indeed jobs with short/empty descriptions
03:30  Fetches each job page (8-12s delay per request)
11:30  Enrichment done, skill-relevant sentences extracted
11:30  [3/5] FILTERING — semantic pre-filter (no Claude API call)
11:30  Auto-index resumes (skips if already indexed)
11:31  Semantic filter: embed each job, query ChromaDB, drop low-similarity
11:31  Attach semantic_score, matched_stack, relevant_chunks to surviving jobs
11:31  Filtered file saved: output/filtered_2026-03-05-11-31-00.json
11:31  [4/5] RANKING — Claude API with RAG context
11:31  Load filtered jobs (skips re-filtering)
11:32  Send to Claude Sonnet with per-job resume context
12:00  Claude responds with scored JSON
12:00  Ranked file saved: output/ranked_2026-03-05-12-00-00.json
12:00  [5/5] REVIEW — interactive terminal review begins
12:00  You approve/skip jobs one by one
~20:00 Review complete, approved jobs imported to tracker
```

**Terminal output:**
```
============================================================
  FULL PIPELINE: Scrape → Enrich → Filter → Rank → Review
============================================================

[1/5] SCRAPING...
10:30:00 [pipeline] INFO: Running indeed scraper...
10:30:45 [pipeline] INFO:   indeed: 1076 jobs
10:30:46 [pipeline] INFO: Running remoteok scraper...
10:30:48 [pipeline] INFO:   remoteok: 45 jobs
10:30:49 [pipeline] INFO: Running arbeitnow scraper...
10:31:02 [pipeline] INFO:   arbeitnow: 69 jobs
10:31:03 [pipeline] INFO: Running rekrute scraper...
10:31:08 [pipeline] INFO:   rekrute: 6 jobs
10:31:09 [pipeline] INFO: Running wttj scraper...
10:33:30 [pipeline] INFO:   wttj: 404 jobs

--- Summary ---
  indeed:    1076 jobs
  remoteok:   45 jobs
  arbeitnow:  69 jobs
  rekrute:     6 jobs
  wttj:      404 jobs
  TOTAL:    1600 jobs (1520 after dedup)
Saved 1520 jobs to output/scraped_2026-03-05-10-30-00.json

[2/5] ENRICHING...
Enriching up to 50 Indeed jobs...
  Enriching 1/50: Senior DevOps Engineer...
  Enriched (420 chars)
  ...
Enrichment done. 47 Indeed jobs now have descriptions.

[3/5] FILTERING...
Loading jobs from output/scraped_2026-03-05-10-30-00.json...
Loaded 1520 jobs. Running semantic filter...
  Semantic filter: kept 820/1520 jobs (threshold=0.65)

============================================================
  SEMANTIC FILTER RESULTS
============================================================
  Input:    1520 jobs
  Kept:     820 jobs
  Dropped:  700 jobs

  By matched stack:
    aws: 310
    azure: 280
    ai: 130
    general: 100

  By source:
    wttj: 390
    indeed: 280
    arbeitnow: 85
    remoteok: 45
    rekrute: 20

  Semantic scores:
    Best:  0.912
    Worst: 0.651
    Avg:   0.743

  Top 10 by semantic score:
    [0.91] [    aws] Senior DevOps Engineer @ Sopra Steria
    [0.89] [  azure] Cloud Platform Engineer @ ING Bank
    ...
============================================================

Filtered jobs saved to output/filtered_2026-03-05-11-31-00.json

[4/5] RANKING...
Found filtered file: filtered_2026-03-05-11-31-00.json
Loading jobs from output/filtered_2026-03-05-11-31-00.json...
Loaded 820 pre-filtered jobs. Sending to Claude for ranking...
  Skipping filter (pre-filtered input): 820 jobs
  Analyzing 820 jobs with claude-sonnet-4-5-20250929...
  Done in 26.1s (14200 in / 7100 out)

  Jobs analyzed: 820
  Average fit:   58
  Top fit:       91
  Distribution:  6 excellent, 14 good, 20 fair, 11 poor

Ranked results saved to output/ranked_2026-03-05-12-00-00.json

[5/5] REVIEW...
Loading ranked jobs from output/ranked_2026-03-03.json...

============================================================
  RANKED JOBS REVIEW — 51 jobs
============================================================

──────────────────────────────────────────────────────────────
  APPLY NOW (6 jobs)
──────────────────────────────────────────────────────────────

  [91/100] Senior DevOps Engineer
  Company:  Sopra Steria
  Location: Paris, France
  Scores:   Skills=92 Exp=90 Loc=95 Growth=85
  Match:    Kubernetes, Terraform, Azure, CI/CD, Docker, ArgoCD
  Missing:  GCP
  [a]pprove | [s]kip | [v]iew full | [q]uit: a
    Imported as #1 in opportunity tracker.

  [87/100] Cloud Platform Engineer
  Company:  ING Bank
  Location: Amsterdam, Netherlands
  Scores:   Skills=88 Exp=85 Loc=90 Growth=82
  Match:    Kubernetes, Terraform, AWS, Prometheus, Grafana
  Missing:  Datadog
  [a]pprove | [s]kip | [v]iew full | [q]uit: v

  URL:     https://ing.com/careers/cloud-platform-engineer-12345
  Source:  indeed
  Resume tweaks:
    - Emphasize multi-cloud (Azure + AWS) experience
    - Highlight Prometheus/Grafana monitoring stack

  [a]pprove | [s]kip | [v]iew full | [q]uit: a
    Imported as #2 in opportunity tracker.

...

Review complete. Approved: 8, Skipped: 43
```

**Files created:**
```
output/scraped_2026-03-05-10-30-00.json    # raw job listings
output/filtered_2026-03-05-11-31-00.json   # semantically filtered jobs
output/ranked_2026-03-05-12-00-00.json     # Claude-scored/ranked jobs
output/opportunities.json                   # approved jobs added to tracker
```

---

## 2. Scrape Only — All Sources

**Command:**
```bash
python scripts/pipeline.py scrape
```

**Timeline: ~3-4 minutes**
```
00:00  Indeed scraper starts (headless browser, 9 country domains)
00:45  Indeed done — ~1000 jobs (snippets only, no full descriptions)
00:47  RemoteOK API call — ~45 jobs (lenient matching catches more)
01:15  Arbeitnow API (15 pages) — ~70 jobs (lenient matching + more pages)
01:30  Rekrute HTML scrape (Morocco) — ~10 jobs
03:30  WTTJ Algolia API (8 keywords x 3 pages) — ~400 jobs
03:30  Dedup + save
```

**Example output file** (`output/scraped_2026-03-03.json`):
```json
{
  "scraped_at": "2026-03-03T10:30:00",
  "total_jobs": 73,
  "jobs": [
    {
      "title": "DevOps Engineer",
      "company": "Sopra Steria",
      "location": "Paris, France",
      "url": "https://fr.indeed.com/viewjob?jk=abc123",
      "source": "indeed",
      "date_posted": "2026-03-01",
      "description": "We are looking for an experienced DevOps Engineer to join our Cloud team. You will design and maintain CI/CD pipelines using Jenkins and GitLab CI, manage Kubernetes clusters on Azure AKS, implement Infrastructure as Code with Terraform...",
      "keyword": "DevOps Engineer",
      "region": "france",
      "scraped_at": "2026-03-03T10:30:15"
    },
    {
      "title": "Senior Cloud Engineer",
      "company": "Remote.com",
      "location": "Remote",
      "url": "https://remoteok.com/remote-jobs/12345",
      "source": "remoteok",
      "date_posted": "2026-03-02",
      "description": "Design and implement cloud infrastructure on AWS and Azure. Experience with Kubernetes, Terraform, and CI/CD pipelines required...",
      "keyword": "Cloud Engineer",
      "region": "remote",
      "scraped_at": "2026-03-03T10:30:47"
    }
  ]
}
```

---

## 3. Scrape Only — API Sources (Fast)

**Command:**
```bash
python scripts/pipeline.py scrape --sources remoteok arbeitnow
```

**Timeline: ~30 seconds** (no headless browser needed)

**Terminal output:**
```
10:30:00 [pipeline] INFO: Running remoteok scraper...
10:30:02 [pipeline] INFO:   remoteok: 12 jobs
10:30:03 [pipeline] INFO: Running arbeitnow scraper...
10:30:18 [pipeline] INFO:   arbeitnow: 18 jobs

--- Summary ---
  remoteok:  12 jobs
  arbeitnow: 18 jobs
  TOTAL:     30 jobs (28 after dedup)
Saved 28 jobs to output/scraped_2026-03-03.json
```

**When to use:** Tuesday/Wednesday/Friday quick checks, or when Indeed is rate-limiting.

---

## 4. Scrape with Custom Keywords & Regions

**Command:**
```bash
python scripts/pipeline.py scrape --sources indeed --keywords "SRE" "Platform Engineer" --regions france netherlands --max-pages 2
```

**Timeline: ~60 seconds** (fewer keywords/regions = faster)

**What changes:**
- Only Indeed scraper runs
- Only 2 keywords instead of 8
- Only 2 regions instead of 9
- Max 2 pages per keyword/region combo (instead of 3)

**Terminal output:**
```
10:30:00 [pipeline] INFO: Running indeed scraper...
10:31:02 [pipeline] INFO:   indeed: 14 jobs
Saved 14 jobs to output/scraped_2026-03-03.json
```

---

## 4b. Speed Up Scraping — Practical Examples

The full `scrape` command (all sources, all keywords, all regions) takes ~5 minutes because Indeed uses a headless browser across 9 domains x 8 keywords x 3 pages with 5-10s delays. Here are faster alternatives:

### Skip Indeed entirely (~2-3 min)

```bash
python scripts/pipeline.py scrape --sources remoteok arbeitnow rekrute wttj
```

API-based scrapers only. No headless browser, no risk of rate-limiting. WTTJ alone returns ~400 jobs via Algolia.

### Limit Indeed to 2 regions (~1 min)

```bash
python scripts/pipeline.py scrape --regions france netherlands
```

Runs all 5 scrapers but Indeed only hits `fr.indeed.com` and `nl.indeed.com` instead of all 9 domains.

### Fewer keywords (~2 min)

```bash
python scripts/pipeline.py scrape --keywords "DevOps Engineer" "Cloud Engineer" "SRE"
```

3 keywords instead of 8 — cuts Indeed page loads by ~60%.

### Reduce pages per source (~2 min)

```bash
python scripts/pipeline.py scrape --max-pages 1
```

1 page per keyword/region instead of 3. Good for daily checks where you only want the newest listings.

### Combine all limits (~1 min)

```bash
python scripts/pipeline.py scrape --regions france netherlands --keywords "DevOps Engineer" "Cloud Engineer" --max-pages 1
```

2 regions x 2 keywords x 1 page = 4 Indeed page loads instead of 216. Plus the fast API scrapers.

### Recommended daily cadence

| Day | Command | Time |
|-----|---------|------|
| Mon | `pipeline.py scrape` (all) | ~5 min |
| Tue | `scrape --sources remoteok arbeitnow rekrute wttj` | ~30 sec |
| Wed | `scrape --sources remoteok arbeitnow rekrute wttj` | ~30 sec |
| Thu | `pipeline.py scrape` (all) | ~5 min |
| Fri | `scrape --sources remoteok arbeitnow rekrute wttj` | ~30 sec |

---

## 5. Index Resumes (Semantic Setup)

**Command (first time or after resume edits):**
```bash
python scripts/pipeline.py index
```

**Command (force reindex):**
```bash
python scripts/pipeline.py index --force
```

**Timeline: ~3 seconds**
```
00:00  Load sentence-transformers model (all-MiniLM-L6-v2)
00:01  Read 6 resume variants (resumes/*/main.md)
00:01  Chunk by ## headings (~46 chunks from resumes)
00:02  Chunk CANDIDATE_CONTEXT by ### headings (~7 chunks)
00:02  Embed all 53 chunks
00:03  Upsert into ChromaDB at output/.chromadb/
00:03  Save index hash for change detection
```

**Terminal output:**
```
Indexing resumes from /path/to/resumes into /path/to/output/.chromadb...
Indexed 53 chunks into ChromaDB.
```

**What gets indexed:**

| Source | Chunks | Metadata |
|--------|--------|----------|
| `ai_eng_*/main.md` | ~8 sections | `stack=ai, lang=en` |
| `ai_fr_*/main.md` | ~8 sections | `stack=ai, lang=fr` |
| `aws_eng_*/main.md` | ~8 sections | `stack=aws, lang=en` |
| `aws_fr_*/main.md` | ~8 sections | `stack=aws, lang=fr` |
| `az_eng_*/main.md` | ~7 sections | `stack=azure, lang=en` |
| `az_fr_*/main.md` | ~7 sections | `stack=azure, lang=fr` |
| `CANDIDATE_CONTEXT` | ~7 sections | `stack=general, lang=en` |

Each chunk includes: section text, stack identifier, language, section name, source file path.

**Subsequent runs (no changes):**
```
Indexing resumes from /path/to/resumes into /path/to/output/.chromadb...
Vector store already up-to-date (use --force to reindex).
```

**How it works under the hood:**
1. Computes MD5 hash of all `main.md` files + `CANDIDATE_CONTEXT`
2. Compares against stored hash in `output/.chromadb/.index_hash`
3. If different: clears collection, re-chunks, re-embeds, upserts
4. If same: skips entirely (fast no-op)

**Fallback chain:**
```
1. Local sentence-transformers (primary, no API calls)
     ↓ ImportError
2. HF Inference API (needs HF_API_TOKEN in .env)
     ↓ No token or API error
3. Keyword-based pre_filter_jobs() (safe fallback, no vector DB needed)
```

---

## 6. Semantic Filter (Standalone)

**Command (auto-find latest scraped file):**
```bash
python scripts/pipeline.py filter
```

**Command (specific file):**
```bash
python scripts/pipeline.py filter --file output/scraped_2026-03-05-23-27-53.json
```

**Command (stricter threshold):**
```bash
python scripts/pipeline.py filter --threshold 0.7
```

**Timeline: ~5-15 seconds** (no API calls, runs locally)
```
00:00  Load scraped JSON
00:01  Auto-index resumes if needed (skips if up-to-date)
00:02  Embed each job's title + description
00:03  Query ChromaDB for top 5 matching resume chunks per job
00:04  Drop jobs below similarity threshold (0.65)
00:05  Save filtered file with breakdown
```

**Terminal output:**
```
Loading jobs from output/scraped_2026-03-05-23-27-53.json...
Loaded 509 jobs. Running semantic filter...
  Semantic filter: kept 320/509 jobs (threshold=0.65)

============================================================
  SEMANTIC FILTER RESULTS
============================================================
  Input:    509 jobs
  Kept:     320 jobs
  Dropped:  189 jobs

  By matched stack:
    aws: 120
    azure: 95
    ai: 60
    general: 45

  By source:
    wttj: 250
    arbeitnow: 40
    remoteok: 30

  Semantic scores:
    Best:  0.912
    Worst: 0.651
    Avg:   0.743

  Top 10 by semantic score:
    [0.91] [    aws] Senior DevOps Engineer @ Sopra Steria
    [0.89] [  azure] Cloud Platform Engineer @ ING Bank
    [0.87] [     ai] MLOps Engineer @ Dataiku
    [0.85] [    aws] Platform Engineer @ Booking.com
    ...
============================================================

Filtered jobs saved to output/filtered_2026-03-05-23-30-00.json
```

**How semantic filtering works per job:**
```
Job: "Senior Platform Engineer — Kubernetes, Terraform, AWS"
  ↓ embed title + description
  ↓ query ChromaDB (top 5 chunks)
  ↓ Best match: aws_eng resume "Professional Summary" (similarity=0.84)
  ↓ matched_stack = "aws"
  ↓ Passes threshold (0.84 > 0.65) → KEEP
  ↓ Attach top 3 resume chunks as RAG context for Claude

Job: "Head Pastry Chef — French Cuisine, Restaurant Management"
  ↓ embed title + description
  ↓ query ChromaDB (top 5 chunks)
  ↓ Best match: aws_fr resume "Langues" section (similarity=0.31)
  ↓ Below threshold (0.31 < 0.65) → DROP
```

**Compared to keyword filter:**
- Keyword: drops jobs missing exact keywords like "kubernetes", "terraform", "docker"
- Semantic: understands that "container orchestration platform" relates to Kubernetes experience
- Semantic: matches "infrastructure automation" to Terraform skills even without the word "terraform"
- Semantic: attaches the best-matching resume variant (AI/AWS/Azure/DevOps) so Claude gets stack-specific context

**What the filtered file contains per job:**
- All original scraped fields (title, company, url, etc.)
- `semantic_score` — cosine similarity (0.0–1.0)
- `matched_stack` — which resume stack matched best (ai/aws/azure/general)
- `relevant_chunks` — top 3 resume sections for RAG context

---

## 7. Rank (Claude AI Scoring)

**Command (auto-find latest filtered file):**
```bash
python scripts/pipeline.py rank
```

**Command (specific file):**
```bash
python scripts/pipeline.py rank --file output/filtered_2026-03-05-23-30-00.json
```

**Command (with role focus):**
```bash
python scripts/pipeline.py rank --role "Platform Engineer"
```

**Timeline: ~30-60 seconds**
```
00:00  Auto-detect latest filtered_*.json (or fall back to scraped_*.json)
00:01  Load pre-filtered jobs (skip semantic filter if using filtered file)
00:02  Slim: strip heavy fields, attach RAG context from matched resume chunks
00:03  Send to Claude Sonnet API (with per-job resume context)
00:35  Response received, parse JSON
00:35  Save ranked file
```

**Terminal output (from filtered file):**
```
Found filtered file: filtered_2026-03-05-23-30-00.json
Loading jobs from output/filtered_2026-03-05-23-30-00.json...
Loaded 320 pre-filtered jobs. Sending to Claude for ranking...
  Skipping filter (pre-filtered input): 320 jobs
  Analyzing 320 jobs with claude-sonnet-4-5-20250929...
  Done in 26.1s (14200 in / 7100 out)

  Jobs analyzed: 320
  Average fit:   64
  Top fit:       93
  Distribution:  8 excellent, 16 good, 18 fair, 6 poor

Ranked results saved to output/ranked_2026-03-05-23-35-00.json
```

**Terminal output (from scraped file, no filtered file available):**
```
Loading jobs from output/scraped_2026-03-05-23-27-53.json...
Loaded 509 jobs. Filtering + sending to Claude for ranking...
  Semantic filter: kept 320/509 jobs (threshold=0.65)
  Analyzing 320 jobs with claude-sonnet-4-5-20250929...
  ...
```

**How rank auto-detects input:**
1. Looks for latest `filtered_*.json` → if found, loads it and skips re-filtering
2. If no filtered file → falls back to latest `scraped_*.json` and runs filter internally

**Example output file** (`output/ranked_2026-03-03.json`):
```json
{
  "search_summary": {
    "total_jobs_analyzed": 51,
    "average_fit_score": 58,
    "top_fit_score": 91,
    "score_distribution": {
      "excellent_80_plus": 6,
      "good_60_79": 14,
      "fair_40_59": 20,
      "poor_below_40": 11
    }
  },
  "ranked_jobs": [
    {
      "rank": 1,
      "title": "Senior DevOps Engineer",
      "company": "Sopra Steria",
      "location": "Paris, France",
      "url": "https://fr.indeed.com/viewjob?jk=abc123",
      "scores": {
        "skills_match": 92,
        "experience_fit": 90,
        "location_fit": 95,
        "growth_potential": 85,
        "overall": 91
      },
      "matching_skills": ["Kubernetes", "Terraform", "Azure", "CI/CD", "Docker", "ArgoCD"],
      "missing_skills": ["GCP"],
      "resume_tweaks": [
        "Emphasize AKS production experience at Marjane Holding",
        "Mention ArgoCD GitOps workflow for deployment automation"
      ],
      "priority": "apply_now"
    },
    {
      "rank": 2,
      "title": "Cloud Platform Engineer",
      "company": "ING Bank",
      "location": "Amsterdam, Netherlands",
      "url": "https://nl.indeed.com/viewjob?jk=def456",
      "scores": {
        "skills_match": 88,
        "experience_fit": 85,
        "location_fit": 90,
        "growth_potential": 82,
        "overall": 87
      },
      "matching_skills": ["Kubernetes", "Terraform", "AWS", "Prometheus", "Grafana"],
      "missing_skills": ["Datadog", "GCP"],
      "resume_tweaks": [
        "Highlight multi-cloud breadth (Azure + AWS)",
        "Add Prometheus/Grafana monitoring dashboards to portfolio"
      ],
      "priority": "apply_now"
    },
    {
      "rank": 15,
      "title": "Junior DevOps Engineer",
      "company": "SmallStartup SAS",
      "location": "Lyon, France",
      "url": "https://www.welcometothejungle.com/jobs/12345",
      "scores": {
        "skills_match": 70,
        "experience_fit": 35,
        "location_fit": 85,
        "growth_potential": 40,
        "overall": 55
      },
      "matching_skills": ["Docker", "CI/CD", "Linux"],
      "missing_skills": ["Kubernetes", "Terraform", "Cloud"],
      "resume_tweaks": [
        "Role is junior — candidate is overqualified, skip unless company is strategic"
      ],
      "priority": "worth_trying"
    }
  ],
  "global_insights": {
    "most_demanded_skills": ["Kubernetes", "Terraform", "AWS", "Docker", "CI/CD"],
    "skills_to_learn": ["GCP", "Datadog", "Pulumi"],
    "market_observations": [
      "Strong demand for multi-cloud engineers in France and Netherlands",
      "Banking sector increasingly requires DevSecOps with compliance focus",
      "Remote-first roles favor AWS over Azure"
    ],
    "recommended_search_refinements": [
      "Add 'Infrastructure Engineer' as a keyword",
      "Consider Datadog monitoring roles for broader match"
    ]
  }
}
```

**What Claude evaluates per job:**

| Dimension | Weight | Example high score | Example low score |
|-----------|--------|--------------------|-------------------|
| Skills Match (40%) | Candidate has 5/6 required skills | Requires GCP-only, no Azure/AWS |
| Experience Fit (30%) | Mid-senior role, 3-5 years needed | Junior role (overqualified) or 10+ years needed |
| Location Fit (15%) | Paris (target city), remote-friendly | Onsite-only in non-target country |
| Growth Potential (15%) | Visa sponsorship, new tech stack | Dead-end maintenance role |

---

## 8. Interactive Review

**Command:**
```bash
python scripts/pipeline.py review
```

**Timeline: 5-15 minutes** (depends on how many jobs you review)

**How it works:**
1. Loads the latest `ranked_*.json` file
2. Groups jobs by priority: `apply_now` → `strong_match` → `worth_trying` → `long_shot` → `skip`
3. Shows each job with scores and skill breakdown
4. You choose an action for each job

**Actions available:**

| Key | Action | What happens |
|-----|--------|-------------|
| `a` | Approve | Job imported to `opportunities.json` with status "New" |
| `s` | Skip | Move to next job |
| `v` | View full | Show URL, source, resume tweaks, then re-prompt |
| `q` | Quit | End review, show approved/skipped counts |

**Example session:**
```
============================================================
  RANKED JOBS REVIEW — 51 jobs
============================================================

──────────────────────────────────────────────────────────────
  APPLY NOW (6 jobs)
──────────────────────────────────────────────────────────────

  [91/100] Senior DevOps Engineer
  Company:  Sopra Steria
  Location: Paris, France
  Scores:   Skills=92 Exp=90 Loc=95 Growth=85
  Match:    Kubernetes, Terraform, Azure, CI/CD, Docker, ArgoCD
  Missing:  GCP
  [a]pprove | [s]kip | [v]iew full | [q]uit: a
    Imported as #1 in opportunity tracker.

──────────────────────────────────────────────────────────────
  STRONG MATCH (14 jobs)
──────────────────────────────────────────────────────────────

  [72/100] DevOps Engineer
  Company:  Orange Business
  Location: Rennes, France
  Scores:   Skills=75 Exp=70 Loc=80 Growth=60
  Match:    Kubernetes, Docker, Jenkins, Linux
  Missing:  Ansible Tower, Puppet
  [a]pprove | [s]kip | [v]iew full | [q]uit: s

──────────────────────────────────────────────────────────────
  WORTH TRYING (20 jobs)
──────────────────────────────────────────────────────────────

  [55/100] Junior DevOps Engineer
  Company:  SmallStartup SAS
  Location: Lyon, France
  Scores:   Skills=70 Exp=35 Loc=85 Growth=40
  Match:    Docker, CI/CD, Linux
  Missing:  Kubernetes, Terraform, Cloud
  [a]pprove | [s]kip | [v]iew full | [q]uit: q

Review ended. Approved: 1, Skipped: 1
```

---

## 9. Application Tracking

### Add a job manually

```bash
python scripts/opportunity_tracker.py add
```

**Interactive session:**
```
--- Add New Opportunity ---
Company: Capgemini
Role: Cloud DevOps Engineer
Location: Paris, France
Remote? (remote/hybrid/onsite): hybrid
Contract (CDI/freelance): CDI
Source (LinkedIn/WTTJ/Indeed/career page/referral/other): LinkedIn
Job URL: https://linkedin.com/jobs/view/12345
Salary/TJM (if known): 55-65k
Notes: Found via recruiter, Python-heavy stack

✓ Added #3: Cloud DevOps Engineer at Capgemini
```

### List all opportunities

```bash
python scripts/opportunity_tracker.py list
```

**Output:**
```
==================================================
  NEW (3)
==================================================
  # 1  Sopra Steria         Senior DevOps Engineer    Paris, France
  # 2  ING Bank             Cloud Platform Engineer   Amsterdam
  # 3  Capgemini            Cloud DevOps Engineer     Paris, France

==================================================
  APPLIED (2)
==================================================
  # 4  BNP Paribas          DevOps Engineer           Paris, France   [hybrid]
        ↳ Follow-up: 2026-03-08
  # 5  Booking.com          SRE                       Amsterdam       [hybrid]
        ↳ Follow-up: 2026-03-07

==================================================
  INTERVIEW (1)
==================================================
  # 6  Orange Business      Platform Engineer         Rennes, France  [hybrid]

Total: 6 opportunities
```

### Update status

```bash
python scripts/opportunity_tracker.py update
```

**Interactive session:**
```
Opportunity ID to update: 1
Current: #1 — Senior DevOps Engineer at Sopra Steria [New]
Statuses: 0=New, 1=Applied, 2=Screening, 3=Interview, 4=Technical, 5=Offer, 6=Accepted, 7=Rejected, 8=Withdrawn
New status (number): 1
  → Applied date set. Follow-up scheduled for 2026-03-08
Notes (enter to skip): Sent CV with cover letter emphasizing AKS
Set follow-up date (YYYY-MM-DD, enter to skip):

✓ Updated #1: New → Applied
```

### Check follow-ups due

```bash
python scripts/opportunity_tracker.py due
```

**Output:**
```
========================================
  FOLLOW-UPS DUE (2026-03-03)
========================================
  # 4  BNP Paribas          DevOps Engineer           [Applied]
        Follow-up date: 2026-03-03
        Notes: Score: 82/100 | Priority: apply_now | Skills: Kubernetes, Azure

  # 5  Booking.com          SRE                       [Applied]
        Follow-up date: 2026-03-02
        Notes: Score: 78/100 | Applied via career page
```

### View statistics

```bash
python scripts/opportunity_tracker.py stats
```

**Output:**
```
========================================
  APPLICATION STATISTICS
========================================

  Total opportunities: 15

  By Status:
    New            5  █████
    Applied        6  ██████
    Screening      1  █
    Interview      1  █
    Rejected       2  ██

  By Source:
    scraper              8
    LinkedIn             4
    career page          2
    referral             1

  By Company (top 10):
    Sopra Steria         2
    Capgemini            2
    BNP Paribas          1
    ING Bank             1

  Response rate: 2/10 = 20%
```

### Bulk import from ranked file

```bash
python scripts/opportunity_tracker.py import
```

**Output:**
```
Imported 12 jobs (3 duplicates skipped) from ranked_2026-03-03.json
```

### Export to Markdown

```bash
python scripts/opportunity_tracker.py export
```

**Output:**
```
✓ Exported to output/opportunities_export.md
```

**Generated file** (`output/opportunities_export.md`):
```markdown
# Opportunities Export — 2026-03-03

| # | Company | Role | Location | Remote | Contract | Source | Status | Applied | Follow-up |
|---|---------|------|----------|--------|----------|--------|--------|---------|-----------|
| 1 | Sopra Steria | Senior DevOps Engineer | Paris | hybrid | CDI | scraper | **Applied** | 2026-03-03 | 2026-03-08 |
| 2 | ING Bank | Cloud Platform Engineer | Amsterdam | hybrid | — | scraper | **New** | — | — |
```

---

## 10. Contact Pipeline

### Add a recruiter

```bash
python scripts/contact_pipeline.py add
```

**Interactive session:**
```
--- Add New Contact ---
Types: 0=Recruiter, 1=Tech Lead, 2=Engineering Manager, 3=Peer Engineer, 4=Business Manager, 5=HR, 6=Other
Contact type (number): 0
Name: Marie Dupont
Company: Sopra Steria
Their role/title: Senior Tech Recruiter
Platform (LinkedIn/email/event/other): LinkedIn
Profile URL: https://linkedin.com/in/marie-dupont
Notes: Recruits for Cloud/DevOps in Paris region

+ Added #1: Marie Dupont (Recruiter) at Sopra Steria
```

### Update with auto follow-up cadence

```bash
python scripts/contact_pipeline.py update
```

**Session — first message sent:**
```
Contact ID to update: 1
Current: #1 — Marie Dupont at Sopra Steria [New]
Statuses: 0=New, 1=Sent, 2=Connected, 3=Replied, 4=Call scheduled, 5=Referred, 6=No response, 7=Not interested
New status (number): 1
  → Message sent. Follow-up #1 scheduled for 2026-03-06
Notes (enter to skip): Sent connection request with note about DevOps role
Override next follow-up date (YYYY-MM-DD, enter to skip):

+ Updated #1: New -> Sent
```

**Session — follow-up #1 sent (3 days later):**
```
Contact ID to update: 1
Current: #1 — Marie Dupont at Sopra Steria [Sent]
New status (number): 1
  → Follow-up #1 sent. Follow-up #2 scheduled for 2026-03-13
```

**Session — follow-up #2 sent (7 days later):**
```
Contact ID to update: 1
Current: #1 — Marie Dupont at Sopra Steria [Sent]
New status (number): 1
  → Follow-up #2 sent. Max follow-ups reached.
```

### Check due follow-ups

```bash
python scripts/contact_pipeline.py due
```

**Output:**
```
=============================================
  CONTACT FOLLOW-UPS DUE (2026-03-03)
=============================================
  # 1  Marie Dupont           Sopra Steria       [Sent]
        Platform: LinkedIn  |  Due: 2026-03-03
        URL: https://linkedin.com/in/marie-dupont

  # 3  John Smith             ING Bank           [Sent]
        Platform: LinkedIn  |  Due: 2026-03-02
        URL: https://linkedin.com/in/john-smith
```

### View stats

```bash
python scripts/contact_pipeline.py stats
```

**Output:**
```
========================================
  CONTACT PIPELINE STATS
========================================

  Total contacts: 8

  By Status:
    New                3  ███
    Sent               3  ███
    Replied            1  █
    No response        1  █

  By Type:
    Recruiter                4
    Tech Lead                2
    Engineering Manager      1
    HR                       1

  By Company (top 10):
    Sopra Steria             2
    Capgemini                2
    ING Bank                 1

  Reply rate: 1/5 = 20%
```

---

## 11. Pipeline Status Check

**Command:**
```bash
python scripts/pipeline.py status
```

**Output:**
```
==================================================
  PIPELINE STATUS
==================================================

  Scraped files: 5
  Latest: scraped_2026-03-03.json
  Total jobs (last 5 files): 342

  Ranked files: 5
  Latest: ranked_2026-03-03.json
  Total ranked (last 5 files): 238

  Tracked opportunities: 15
    New: 5
    Applied: 6
    Screening: 1
    Interview: 1
    Rejected: 2

  Tracked contacts: 8

==================================================
```

---

## 12. Manual Search URLs

**Command (print all):**
```bash
./scripts/job_search_queries.sh
```

**Command (open in browser):**
```bash
./scripts/job_search_queries.sh --open
```

**Covers 100+ pre-built search URLs across:**

| Platform | Searches |
|----------|----------|
| LinkedIn | 13 (by role + region) |
| Welcome to the Jungle | 6 |
| Indeed France | 4 |
| APEC | 3 |
| Free-Work | 4 |
| StepStone (Germany) | 5 |
| Netherlands platforms | 3 |
| Belgium/Luxembourg | 2 |
| Switzerland | 2 |
| UK platforms | 3 |
| Morocco/MENA | 3 |
| Gulf (Saudi/Qatar) | 3 |
| Canada | 2 |
| Remote-first boards | 3 |
| Company career pages | 15 (Sopra, Capgemini, BNP, Orange, etc.) |

---

## Execution Cheat Sheet

| Goal | Command | Time |
|------|---------|------|
| Full daily run | `pipeline.py run` | ~20 min (enrich adds ~8 min) |
| Quick API scrape | `pipeline.py scrape --sources remoteok arbeitnow wttj` | ~2-3 min |
| Enrich Indeed descriptions | `pipeline.py enrich --max-enrich 10` | ~2 min |
| Index resumes | `pipeline.py index` | ~3 sec (skips if unchanged) |
| Force reindex | `pipeline.py index --force` | ~3 sec |
| Semantic filter only | `pipeline.py filter` | ~5-15 sec (no API call) |
| Stricter filter | `pipeline.py filter --threshold 0.7` | ~5-15 sec |
| Rank (Claude scoring) | `pipeline.py rank` | ~30 sec (auto-uses filtered file) |
| Review ranked jobs | `pipeline.py review` | ~5-15 min |
| Check what to follow up | `opportunity_tracker.py due` | instant |
| Add job from LinkedIn | `opportunity_tracker.py add` | ~1 min |
| Update application status | `opportunity_tracker.py update` | ~30 sec |
| Weekly stats | `opportunity_tracker.py stats` | instant |
| Weekly export | `opportunity_tracker.py export` | instant |
| Add recruiter contact | `contact_pipeline.py add` | ~1 min |
| Check contact follow-ups | `contact_pipeline.py due` | instant |
| Pipeline health | `pipeline.py status` | instant |

---

## Recommended Weekly Schedule

| Day | Scraping | Manual Search | Focus |
|-----|----------|---------------|-------|
| Monday | `pipeline.py run` (all sources) | LinkedIn | Full sweep + applications |
| Tuesday | `scrape` + `filter` + `rank` (API only) | WTTJ | EU remote jobs |
| Wednesday | `scrape` + `filter` + `rank` (API only) | Company career pages | Direct applications |
| Thursday | `pipeline.py run` (all sources) | LinkedIn | Full sweep + follow-ups |
| Friday | `scrape` + `filter` + `rank` (API only) | StepStone/Germany | EU expansion |
| Sunday | — | — | `stats` + `export` + weekly review |
