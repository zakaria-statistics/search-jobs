# Job Search Pipeline

An automated job search system that scrapes jobs from 5 platforms, uses semantic filtering to pre-screen against your resumes, then Claude AI to rank survivors, provides interactive human-in-the-loop review, and tracks applications and recruiter outreach through their full lifecycle.

## Architecture

```
[SCRAPE]          [ENRICH]       [INDEX]           [FILTER]            [RANK]            [REVIEW]          [TRACK]
5 job sources --> Indeed desc -> Resumes into  --> Semantic filter --> Claude AI     --> Human review  --> Application &
~500+ jobs       fetch (top 50)  ChromaDB          drop low-match     RAG-enhanced      approve/skip      contact management
                 skill-filter    (one-time)        save filtered_*    scores 0-100      view details       follow-up reminders
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

# Run each step individually (controlled pace)
python scripts/pipeline.py scrape                    # Scrape job sources
python scripts/pipeline.py enrich                    # Fetch full Indeed descriptions
python scripts/pipeline.py filter                    # Semantic filter (no Claude API call)
python scripts/pipeline.py rank                      # Claude ranking (uses filtered file)
python scripts/pipeline.py review                    # Interactive human review

# Or run the full pipeline at once
python scripts/pipeline.py run

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
│   ├── rank.py                  # Slim, Claude API call, parse (accepts pre-filtered input)
│   ├── vectorstore.py           # ChromaDB vector store: index resumes, query jobs
│   └── semantic_filter.py       # Semantic job filtering using resume embeddings
│
├── scripts/                     # CLI tools
│   ├── pipeline.py              # Main orchestrator (scrape|enrich|index|filter|rank|review|run|manual|status)
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
├── resumes/                     # Resume variants (8 total, gitignored)
│   ├── ai_eng_.../main.md       # AI stack, English
│   ├── ai_fr_.../main.md        # AI stack, French
│   ├── aws_eng_.../main.md      # AWS stack, English
│   ├── aws_fr_.../main.md       # AWS stack, French
│   ├── az_eng_.../main.md       # Azure stack, English
│   ├── az_fr_.../main.md        # Azure stack, French
│   ├── devops_eng_.../main.md   # DevOps stack, English
│   └── devops_fr_.../main.md    # DevOps stack, French
│
├── output/                      # Generated data (gitignored)
│   ├── .chromadb/               # ChromaDB vector store (auto-created)
│   ├── scraped_YYYY-MM-DD-HH-MM-SS.json   # Timestamped raw job listings
│   ├── filtered_YYYY-MM-DD-HH-MM-SS.json  # Semantically filtered jobs
│   ├── ranked_YYYY-MM-DD-HH-MM-SS.json    # Claude-ranked + scored jobs
│   ├── opportunities.json       # Application tracker state
│   └── contacts.json            # Contact tracker state
│
├── ARCHITECTURE.md              # System design documentation
├── WORKFLOW.md                  # Daily/weekly execution guide
├── WALKTHROUGH.md               # Detailed execution examples & timelines
├── VECTORDB_BREAKDOWN.md        # How the vector DB and embeddings work
└── requirements.txt             # Python dependencies
```

## Pipeline Commands

### Main Pipeline (`pipeline.py`)

| Command | Description |
|---------|-------------|
| `scrape` | Run all or selected scrapers |
| `enrich` | Fetch full Indeed job descriptions (top 50) |
| `index` | Index resumes into ChromaDB (auto-runs on first `filter`) |
| `filter` | Semantic pre-filter only — no Claude API call, saves `filtered_*.json` |
| `rank` | Claude AI scoring (auto-uses `filtered_*.json` if available, skips re-filtering) |
| `review` | Interactive terminal review (approve/skip/view) |
| `run` | Full chain: scrape + enrich + filter + rank + review |
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

### Stage 1: Semantic Pre-filter (`pipeline.py filter`)

A standalone step that runs before Claude. Powered by ChromaDB and sentence-transformers:

1. **Indexing** (one-time): 8 resume variants (AI/AWS/Azure/DevOps x EN/FR) and the candidate context are chunked by `##` headings, embedded with `all-MiniLM-L6-v2`, and stored in ChromaDB at `output/.chromadb/`
2. **Per-job query**: Each job's `title + description` is embedded and compared against resume chunks via cosine similarity
3. **Filtering**: Jobs below the similarity threshold (default 0.65) are dropped
4. **Enrichment**: Surviving jobs get `semantic_score`, `matched_stack` (ai/aws/azure), and `relevant_chunks` attached
5. **Output**: Saves `filtered_YYYY-MM-DD-HH-MM-SS.json` with breakdown (stacks, sources, score distribution, top 10)

```bash
python scripts/pipeline.py filter                    # Default threshold (0.65)
python scripts/pipeline.py filter --threshold 0.7    # Stricter filtering
python scripts/pipeline.py filter --file output/scraped_2026-03-05-23-27-53.json  # Specific file
```

**Fallback chain**: If ChromaDB or sentence-transformers are unavailable, falls back to keyword-based filtering automatically.

### Stage 2: RAG-Enhanced Claude Ranking (`pipeline.py rank`)

Automatically picks up the latest `filtered_*.json` and skips re-filtering. If no filtered file exists, it runs the semantic filter internally first.

Jobs are sent to Claude with their matched resume chunks included as context. Claude sees:
- The slimmed job data (title, description, location, etc.)
- The most relevant resume sections for that specific job (stack-aware)
- The pre-computed semantic score

```bash
python scripts/pipeline.py rank                      # Auto-uses latest filtered file
python scripts/pipeline.py rank --file output/filtered_2026-03-05-23-30-00.json  # Specific file
python scripts/pipeline.py rank --role "Platform Engineer"   # Role focus
```

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

1. `python scripts/pipeline.py scrape --sources remoteok arbeitnow wttj` — quick scrape (2 min)
2. `python scripts/pipeline.py filter` — see what passes semantic filter (instant)
3. `python scripts/pipeline.py rank` — Claude scoring on filtered jobs (30 sec)
4. `python scripts/pipeline.py review` — approve/skip ranked jobs (5 min)
5. `python scripts/opportunity_tracker.py due` — check follow-ups (5 min)
6. Manual search on LinkedIn/WTTJ (20 min)
7. Apply to top-ranked jobs (20 min)
8. `python scripts/contact_pipeline.py due` — recruiter follow-ups (5 min)

## Resume Management

The system uses 8 resume variants under `resumes/`, each tailored to a different stack and language:

| Directory | Stack | Language |
|-----------|-------|----------|
| `ai_eng_*/main.md` | AI/MLOps | English |
| `ai_fr_*/main.md` | AI/MLOps | French |
| `aws_eng_*/main.md` | AWS Cloud | English |
| `aws_fr_*/main.md` | AWS Cloud | French |
| `az_eng_*/main.md` | Azure Cloud | English |
| `az_fr_*/main.md` | Azure Cloud | French |
| `devops_eng_*/main.md` | DevOps | English |
| `devops_fr_*/main.md` | DevOps | French |

When you update a resume, the vector store auto-reindexes on the next `filter` run (hash-based change detection). To force reindex: `python scripts/pipeline.py index --force`.
