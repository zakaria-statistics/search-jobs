# Job Search Pipeline

An automated job search system that scrapes jobs from 5 platforms, uses semantic filtering to pre-screen against your resumes, then Claude AI to rank survivors, provides interactive human-in-the-loop review, and tracks applications and recruiter outreach through their full lifecycle.

## Architecture

```
[SCRAPE]          [ENRICH]       [INDEX]           [FILTER]            [RANK]            [REVIEW]          [TRACK]
5 job sources --> Indeed desc -> Resumes into  --> Semantic filter --> Claude AI     --> Human review  --> Application &
~500+ jobs       fetch (top 50)  ChromaDB          drop low-match     RAG-enhanced      approve/skip      contact management
                 skill-filter    (one-time)        save filtered_*    scores 0-100      view details       follow-up reminders
```

## Documentation

| File | Purpose |
|------|---------|
| [GUIDE.md](GUIDE.md) | Daily workflow, commands, examples |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical deep-dive, modules, data formats |
| [MILESTONE.md](MILESTONE.md) | Project evolution through phases |
| [VECTORDB_BREAKDOWN.md](VECTORDB_BREAKDOWN.md) | How the vector DB and embeddings work |

## Quick Start

```bash
cd job-search
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure API keys in .env
ANTHROPIC_API_KEY=sk-ant-...

# Run the full pipeline
python scripts/pipeline.py run

# Or run steps individually
python scripts/pipeline.py scrape
python scripts/pipeline.py enrich
python scripts/pipeline.py filter
python scripts/pipeline.py rank
python scripts/pipeline.py review
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
│   ├── runs/                    # Pipeline run outputs
│   │   └── YYYY-MM-DD-HH-MM-SS/
│   │       ├── scraped.json     # Raw job listings
│   │       ├── filtered.json    # Semantically filtered jobs
│   │       └── ranked.json      # Claude-ranked + scored jobs
│   ├── opportunities.json       # Application tracker state
│   └── contacts.json            # Contact tracker state
│
├── ARCHITECTURE.md              # System design documentation
├── GUIDE.md                     # Daily workflow, commands, examples
├── MILESTONE.md                 # Project evolution through phases
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

### How matching works

Jobs are matched in 5 tiers (first match wins) via `scraper/config.py:match_job()`. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full module breakdown.

## Configuration

All tunable settings live in two config files:

- **`scraper/config.py`** — search keywords, target regions, per-source rate limits, keyword matching patterns
- **`ranker/config.py`** — candidate profile, skill keywords, Claude model settings, semantic filter settings (model, threshold, paths)

## Dependencies

```
scrapling[all]          # HTML scraping (Fetcher, StealthyFetcher)
requests                # HTTP for REST API scrapers
anthropic               # Claude API for job ranking
python-dotenv           # Load .env file
chromadb                # Vector database for semantic search
sentence-transformers   # Local embedding model (all-MiniLM-L6-v2)
```

## Resume Management

The system uses 8 resume variants under `resumes/`, each tailored to a different stack (AI/AWS/Azure/DevOps) and language (English/French).

When you update a resume, the vector store auto-reindexes on the next `filter` run (hash-based change detection). To force reindex: `python scripts/pipeline.py index --force`.
