# Job Search Pipeline

An automated job search system that scrapes jobs from 5 platforms, uses Claude AI to rank them against your candidate profile, provides interactive human-in-the-loop review, and tracks applications and recruiter outreach through their full lifecycle.

## Architecture

```
[SCRAPE]          [ENRICH]       [INDEX]           [RANK]              [REVIEW]          [TRACK]
5 job sources --> Indeed desc -> Resumes into  --> Semantic filter --> Human review  --> Application &
~500+ jobs       fetch (top 50)  ChromaDB          + Claude AI        approve/skip      contact management
                 skill-filter    (one-time)        RAG-enhanced       view details       follow-up reminders
                                                   scores 0-100
```

## Quick Start

```bash
cd job-search

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure API keys in .env
ANTHROPIC_API_KEY=sk-ant-...
HF_API_TOKEN=hf_...              # Optional: only needed if sentence-transformers unavailable

# Index resumes into ChromaDB (one-time, auto-reindexes on resume changes)
python scripts/pipeline.py index

# Run the full pipeline (scrape + enrich + rank + review)
python scripts/pipeline.py run

# Or run each step individually
python scripts/pipeline.py scrape
python scripts/pipeline.py enrich             # Fetch full Indeed descriptions
python scripts/pipeline.py rank               # Semantic filter + Claude ranking
python scripts/pipeline.py review

# Check pipeline health
python scripts/pipeline.py status
```

> Always run `source .venv/bin/activate` before using any pipeline command.

## Project Structure

```
job-search/
├── scraper/                     # Job scraping module (5 sources)
│   ├── base.py                  # BaseScraper abstract class
│   ├── models.py                # Job dataclass
│   ├── config.py                # Keywords, regions, rate limits, match_job()
│   ├── description_utils.py     # Skill-sentence extraction from HTML descriptions
│   ├── storage.py               # JSON persistence & deduplication
│   ├── indeed.py                # Indeed (9 country domains, headless browser + enrich)
│   ├── remoteok.py              # RemoteOK (REST API, global remote jobs)
│   ├── arbeitnow.py             # Arbeitnow (REST API, EU-focused, 15 pages)
│   ├── rekrute.py               # Rekrute (Morocco)
│   └── wttj.py                  # Welcome to the Jungle (Algolia API)
│
├── ranker/                      # Semantic filtering + Claude-powered ranking
│   ├── config.py                # Candidate profile, skill keywords, Claude & semantic settings
│   ├── prompts.py               # System prompt with scoring criteria + RAG instructions
│   ├── rank.py                  # Filter, slim, Claude API call, parse
│   ├── vectorstore.py           # ChromaDB vector store: index resumes, query jobs
│   └── semantic_filter.py       # Semantic job filtering using resume embeddings
│
├── scripts/                     # CLI tools
│   ├── pipeline.py              # Main orchestrator (scrape|rank|review|run|manual|status)
│   ├── opportunity_tracker.py   # Application tracking (add|list|update|stats|export|due|import)
│   ├── contact_pipeline.py      # Recruiter outreach (add|list|update|stats|export|due)
│   └── job_search_queries.sh    # 100+ pre-built search URLs across 15+ platforms
│
├── docs/                        # Strategy & planning documents
│   ├── 01_candidate_target.md   # Profile, target roles, positioning
│   ├── 02_company_goals.md      # Sector analysis (banking, telecom, retail, ESN)
│   ├── 03_opportunities_map.md  # Platform URLs, company career pages
│   └── 04_job_platforms.md      # Platform tiers & daily/weekly cadence
│
├── resumes/                     # Resume variants (6 total, gitignored)
│   ├── ai_eng_.../main.md       # AI stack, English
│   ├── ai_fr_.../main.md        # AI stack, French
│   ├── aws_eng_.../main.md      # AWS stack, English
│   ├── aws_fr_.../main.md       # AWS stack, French
│   ├── az_eng_.../main.md       # Azure stack, English
│   └── az_fr_.../main.md        # Azure stack, French
│
├── output/                      # Generated data (gitignored)
│   ├── .chromadb/               # ChromaDB vector store (auto-created)
│   ├── scraped_YYYY-MM-DD.json  # Daily raw job listings
│   ├── ranked_YYYY-MM-DD.json   # Daily ranked + scored jobs
│   ├── opportunities.json       # Application tracker state
│   └── contacts.json            # Contact tracker state
│
├── ARCHITECTURE.md              # System design documentation
├── WORKFLOW.md                  # Daily/weekly execution guide
├── WALKTHROUGH.md               # Detailed execution examples & timelines
└── requirements.txt             # Python dependencies
```

## Pipeline Commands

### Main Pipeline (`pipeline.py`)

| Command | Description |
|---------|-------------|
| `scrape` | Run all or selected scrapers |
| `enrich` | Fetch full Indeed job descriptions (top 50) |
| `index` | Index resumes into ChromaDB (auto-runs on first `rank`) |
| `rank` | Semantic filter + Claude AI scoring |
| `review` | Interactive terminal review (approve/skip/view) |
| `run` | Full chain: scrape + enrich + rank + review |
| `manual` | Add a job manually to the tracker |
| `status` | Show pipeline health and statistics |

### Application Tracker (`opportunity_tracker.py`)

| Command | Description |
|---------|-------------|
| `add` | Add a new opportunity interactively |
| `list` | List all opportunities grouped by status |
| `update` | Update status (auto-sets follow-up dates) |
| `stats` | Show distribution by status, source, company |
| `export` | Generate Markdown table export |
| `due` | Show follow-ups due today |
| `import` | Bulk import from ranked JSON files |

### Contact Pipeline (`contact_pipeline.py`)

| Command | Description |
|---------|-------------|
| `add` | Add recruiter/tech lead with platform info |
| `list` | List contacts grouped by outreach status |
| `update` | Update status with auto-scheduled follow-ups |
| `stats` | Response rates by status and type |
| `export` | Generate Markdown export |
| `due` | Show follow-ups due today |

## Data Sources

| Source | Method | Coverage | Typical yield | Speed |
|--------|--------|----------|---------------|-------|
| Indeed | Headless browser | 9 countries (MA, FR, DE, NL, BE, LU, PL, CH, UK) | ~1000 jobs | ~5-8 min |
| WTTJ | Algolia API | France + EU (startups & corporates) | ~400 jobs | ~2 min |
| Arbeitnow | REST API (15 pages) | EU-focused | ~70 jobs | ~30 sec |
| RemoteOK | REST API | Global remote jobs | ~45 jobs | ~10 sec |
| Rekrute | HTML scraping | Morocco | ~10 jobs | ~30 sec |

### How matching works (`scraper/config.py:match_job()`)

Jobs are matched in 5 tiers (first match wins):

1. Full keyword phrase in title (e.g. "DevOps Engineer" in title)
2. Role terms as whole words in title (e.g. `\bdevops\b`, `\bcloud\b`)
3. Full keyword phrase in tags
4. Strict role terms in tags (devops, mlops, sre, kubernetes only)
5. **Lenient** (RemoteOK, Arbeitnow, WTTJ only): description contains 2+ skill keywords from `ranker/config.py:CANDIDATE_SKILL_KEYWORDS`

Tier 5 catches jobs with non-standard titles (e.g. "Infrastructure Specialist" whose description mentions kubernetes + terraform).

### Description handling

| Source | Raw description | After processing |
|--------|----------------|-----------------|
| Indeed (search) | Snippet only (~1 sentence) | `enrich` fetches full page, `extract_skill_sentences()` keeps only skill-relevant lines |
| RemoteOK | Full HTML in API response | Truncated to 500 chars |
| Arbeitnow | Full HTML in API response | Truncated to 500 chars |
| WTTJ | `profile` field from Algolia | Up to 500 chars + contract/salary metadata |
| Ranker (`slim_job`) | Any description > 600 chars | `extract_skill_sentences()` picks skill-relevant sentences instead of blind truncation |

## Semantic Filtering + AI Ranking

### Stage 1: Semantic Pre-filter (Vector DB + Embeddings)

Before jobs reach Claude, they pass through a semantic filter powered by ChromaDB and sentence-transformers:

1. **Indexing** (one-time): 6 resume variants (AI/AWS/Azure x EN/FR) and the candidate context are chunked by `##` headings, embedded with `all-MiniLM-L6-v2`, and stored in ChromaDB at `output/.chromadb/`
2. **Per-job query**: Each job's `title + description` is embedded and compared against resume chunks via cosine similarity
3. **Filtering**: Jobs below the similarity threshold (default 0.65) are dropped
4. **Enrichment**: Surviving jobs get `semantic_score`, `matched_stack` (ai/aws/azure), and `relevant_chunks` attached

This replaces the old keyword-based pre-filter (40+ hardcoded terms) with semantic understanding. A "Kubernetes Platform Engineer" job now matches even if none of the exact keywords appear in its description.

**Fallback chain**: If ChromaDB or sentence-transformers are unavailable, the system falls back to keyword-based filtering automatically.

### Stage 2: RAG-Enhanced Claude Ranking

Jobs that pass the semantic filter are sent to Claude with their matched resume chunks included as context. Claude sees:
- The slimmed job data (title, description, location, etc.)
- The most relevant resume sections for that specific job (stack-aware)
- The pre-computed semantic score

This gives Claude richer, per-job candidate context instead of a single generic profile.

### Scoring Dimensions

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Skills Match | 40% | How many required skills the candidate has |
| Experience Fit | 30% | Seniority and years match |
| Location Fit | 15% | Target region, remote-friendliness |
| Growth Potential | 15% | Career progression, learning, visa sponsorship |

Priority labels assigned based on overall score:
- **apply_now** (80+) — strong match, apply immediately
- **strong_match** (60-79) — good fit, worth applying
- **worth_trying** (40-59) — partial fit
- **long_shot** (<40) — low match
- **skip** — not relevant

## Configuration

### Search Keywords (`scraper/config.py`)

8 default keywords: DevOps Engineer, Cloud Engineer, MLOps Engineer, Platform Engineer, Site Reliability Engineer, Kubernetes Engineer, AI Infrastructure Engineer, Cloud Architect

### Candidate Profile (`ranker/config.py`)

Hard-coded profile including technical skills, experience, target roles, differentiators, and target regions. Edit this file to customize for a different candidate.

### Semantic Filter (`ranker/config.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `SEMANTIC_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |
| `SEMANTIC_THRESHOLD` | `0.65` | Minimum cosine similarity to keep a job |
| `CHROMADB_DIR` | `output/.chromadb/` | Persistent vector store location |
| `RESUMES_DIR` | `resumes/` | Directory containing resume variants |
| `USE_SEMANTIC_FILTER` | `True` | Set `False` to use keyword filter instead |
| `HF_API_TOKEN` | env `HF_API_TOKEN` | Fallback: HF Inference API if no local model |

### Pre-filter Keywords (`ranker/config.py`)

34 skill keywords used as fallback when semantic filter is unavailable.

## Dependencies

```
scrapling[all]          # HTML scraping (Fetcher, StealthyFetcher)
requests                # HTTP for REST API scrapers
anthropic               # Claude API for job ranking
python-dotenv           # Load .env file
chromadb                # Vector database for semantic search
sentence-transformers   # Local embedding model (all-MiniLM-L6-v2)
```

## Application Status Flow

```
New --> Applied --> Screening --> Interview --> Technical --> Offer --> Accepted
                                                                  --> Rejected
                                                                  --> Withdrawn
```

## Contact Outreach Cadence

```
Day 0: Initial message sent     --> follow-up #1 in 3 days
Day 3: Follow-up #1             --> follow-up #2 in 7 days
Day 10: Follow-up #2            --> pause (max follow-ups reached)
```

## Recommended Daily Routine (~1 hour)

1. `python scripts/pipeline.py run` — automated scrape + semantic rank + review (10 min)
2. `python scripts/opportunity_tracker.py due` — check follow-ups (5 min)
3. Manual search on LinkedIn/WTTJ (20 min)
4. Apply to top-ranked jobs (20 min)
5. `python scripts/contact_pipeline.py due` — recruiter follow-ups (5 min)

## Resume Management

The system uses 6 resume variants under `resumes/`, each tailored to a different stack and language:

| Directory | Stack | Language |
|-----------|-------|----------|
| `ai_eng_*/main.md` | AI/MLOps | English |
| `ai_fr_*/main.md` | AI/MLOps | French |
| `aws_eng_*/main.md` | AWS Cloud | English |
| `aws_fr_*/main.md` | AWS Cloud | French |
| `az_eng_*/main.md` | Azure Cloud | English |
| `az_fr_*/main.md` | Azure Cloud | French |

When you update a resume, the vector store auto-reindexes on the next `rank` run (hash-based change detection). To force reindex: `python scripts/pipeline.py index --force`.
