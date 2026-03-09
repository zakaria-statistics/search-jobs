# CLAUDE.md — Project Guidelines

## Project Identity

Job search automation pipeline: scrape -> filter -> rank -> review -> track.
Mono-repo at `/root/search/`, all code under `job-search/`.

## Architecture Map

```
scraper/          ranker/                    scripts/
 6 scrapers  -->  semantic_filter.py    -->  pipeline.py (orchestrator)
 config.py       composite_score.py          opportunity_tracker.py
 storage.py       vectorstore.py             contact_pipeline.py
 models.py        rank.py (Claude API)
 url_validator.py  config.py
 linkedin.py      prompts.py
```

### Data Flow (sequential, left-to-right)

```
scrape -> output/runs/{ts}/scraped.json
       -> enrich (Indeed full descriptions)
       -> filter -> filtered_top.json, filtered_strong.json, filtered_moderate.json
       -> validate -> validated.json (live), closed.json (dropped)
       -> prepare -> prepared.json (slim for Claude, inspectable)
       -> rank   -> ranked.json  (Claude API call)
       -> review -> opportunities.json (persistent, shared)
```

### Dependency Direction (who imports who)

```
pipeline.py --> scraper/* (scrape, validate), ranker/* (filter, rank)
semantic_filter.py --> vectorstore.py, composite_score.py, config.py
rank.py --> semantic_filter.py (when skip_filter=False), config.py, prompts.py
composite_score.py --> config.py (weights, patterns, locations)
url_validator.py --> scraper/config.py (delay constants), scrapling, requests
linkedin.py --> base.py, config.py, models.py, requests, bs4 (+ DataImpulse proxy via env)
storage.py --> models.py
all scrapers --> base.py, config.py, models.py
```

### Global Shared State vs Local

- **Global (persistent):** `output/opportunities.json`, `output/contacts.json`, `output/.chromadb/`
- **Per-run (ephemeral):** `output/runs/{timestamp}/` — scraped, filtered, validated, prepared, ranked files
- **Symlink:** `output/latest -> runs/{most-recent-timestamp}/`
- **Config (shared constants):** `scraper/config.py` (keywords, regions), `ranker/config.py` (profile, weights, thresholds)
- **Secrets:** `.env` (gitignored) — API keys, DataImpulse proxy credentials; loaded by `pipeline.py` at startup

### Component Classification

**Core classes & methods:**
- `BaseScraper` (scraper/base.py) — ABC for all scrapers
- `Job` dataclass (scraper/models.py) — canonical job representation
- `semantic_filter_jobs()` (ranker/semantic_filter.py) — main filter entry point
- `compute_composite_score()` (ranker/composite_score.py) — 5-signal scorer
- `rank_jobs()` (ranker/rank.py) — Claude API ranking
- `validate_jobs()` (scraper/url_validator.py) — batch URL liveness checking
- `cmd_*()` functions in pipeline.py — CLI command handlers

**Helpers & utils:**
- `slim_job()` (ranker/rank.py) — strips heavy fields for token efficiency
- `prepare_jobs()` (ranker/rank.py) — batch slim_job() for all jobs
- `_call_claude()` (ranker/rank.py) — single streamed API call for one batch
- `_merge_results()` (ranker/rank.py) — combines batch results, re-ranks globally
- `extract_skill_sentences()` (scraper/description_utils.py) — NLP-lite skill extraction
- `_create_run_dir()` (scripts/pipeline.py) — output dir management
- `_find_latest_file()` (scripts/pipeline.py) — file discovery with fallback chain
- `check_single_url()` (scraper/url_validator.py) — single URL liveness check
- `drop_closed()` (scraper/url_validator.py) — split jobs into live/closed
- `build_relevance()` (ranker/relevance.py) — per-stage summary block for JSON outputs
- `cmd_sync()` (scripts/pipeline.py) — rclone-based sync to Google Drive

**Config:**
- `scraper/linkedin.py` — LinkedInScraper, guest API + DataImpulse proxy, byte budget tracking
- `scraper/config.py` — search keywords, regions, rate limits, validation delays, `match_job()` 5-tier matching
- `ranker/config.py` — candidate profile, skill keywords, composite weights, semantic settings

## Working Rules

### 1. Propagate Changes to Documentation

When adding, modifying, or removing a feature/concept:
- Update `ARCHITECTURE.md` if data flow, modules, or formats changed
- Update `GUIDE.md` if CLI commands, flags, or workflow changed
- Update `MILESTONE.md` if this is a new phase or significant capability
- Update `README.md` only if project structure or quick-start changed
- Update this `CLAUDE.md` if dependency direction, components, or shared state changed

### 2. Change Impact Assessment

Before starting work, classify and state the change grade:

| Grade | Scope | Example |
|-------|-------|---------|
| **G1 — Patch** | Single file, no API/flow change | Fix a regex, adjust a weight |
| **G2 — Local** | 1-2 files, same module | Add a flag to a command, new helper |
| **G3 — Cross-module** | Multiple modules, data flow intact | New scoring signal, new scraper |
| **G4 — Structural** | Data flow changes, new stage, schema change | New pipeline stage, output format change |
| **G5 — Redesign** | Architecture change, breaking | Replace vector DB, new orchestrator |

State the grade and affected files before starting. Example: "G3 — adds stack_depth signal. Touches: composite_score.py, config.py, semantic_filter.py. Downstream: filtered output gets new field."

### 3. Explain With Dependency Direction

When explaining changes or code:
- Show what depends on what (A --> B means A imports/calls B)
- Indicate read order: sequential (step 1 then 2), parallel (independent), or overlapping (shared state)
- Show before/after when modifying behavior
- Name the upstream (who provides) and downstream (who consumes) for any data

### 4. Detect Drift and Manual Changes

Before making changes:
- Check `git status` for uncommitted work or new directories
- Look for files/dirs that don't match the known structure (e.g., `concepts/`, `debug/`)
- If found, ask before overwriting or deleting — these may be user's in-progress work
- Note any config values that differ from defaults (user may have tuned them)

### 5. Design Philosophy (see `plan/design_philosophy.md` for full breakdown)

- **Prototype first:** New ideas start in `concepts/` — validate before integrating
- **Promote when ready:** Move to pipeline module only when it needs upstream data and has proven value
- **Loose coupling:** Modules communicate through JSON files, not cross-boundary imports
- **Don't architect unvalidated ideas:** One phase ahead is planning, two is speculation
- **Growth path:** Idea -> Experiment -> Standalone script -> Pipeline module -> Integrated feature

### 6. Minimal Changes by Default

- Make the smallest change that solves the problem
- Don't refactor surrounding code unless asked ("refactor", "redo", "clean up")
- Don't add docstrings, type hints, or comments to code you didn't change
- Don't create abstractions for one-time operations
- If the user says "refactor" or "redo", then broader changes are authorized

### 6. Use Plan Mode for Non-Trivial Work

Enter plan mode and ask clarifying questions when:
- Change is G3 or above
- Requirements are ambiguous
- Multiple valid approaches exist
- Change touches shared state or persistent data

**Ask before building:** For G3+ features, ask clarifying questions to understand the user's full intent before writing code or a plan. Don't assume scope, data sources, or priorities — surface unknowns early. Even for G2, if the goal is ambiguous, ask rather than guess.

**Offer choices:** When multiple valid approaches exist, present them as numbered options with trade-offs (e.g., cost, complexity, time). Let the user pick direction rather than choosing silently. Format: `1. Option — trade-off | 2. Option — trade-off`

### 7. Parameterized Context for Prompts (PCTF)

When working with agents or complex tasks, structure prompts with:

```
CONTEXT:  {what exists, current state}
TARGET:   {desired outcome}
FILES:    {specific files to read/modify}
CONSTRAINTS: {what NOT to change, backward compat needs}
```

### 8. Follow Execution Mechanisms

Be aware of the pipeline's execution chain:
- **Timestamps:** Each run creates `output/runs/{YYYY-MM-DD-HH-MM-SS}/`
- **Stages:** scrape -> enrich -> filter -> validate -> prepare -> rank -> review (sequential)
- **Milestones:** Tracked in MILESTONE.md by phase
- **State:** `_run_dir` passed through `args` across stages within `cmd_run()`
- **Discovery:** `_find_latest_file()` checks latest symlink -> runs dirs -> legacy flat files

### 9. Logging and Observability

When writing or modifying scripts that the user runs:
- **Always include meaningful log output** so the user can follow what's happening in real time
- **Show progress:** stage transitions ("Scraping...", "Filtering 509 jobs..."), counts, and timing
- **Show results:** summary stats at the end (kept/dropped, scores, top N preview)
- **Show decisions:** when the code makes a choice (e.g., "Found filtered file, skipping re-filter"), log why
- **Show errors with context:** not just the exception, but what was being attempted and what to try next
- **Use structured output:** tables, aligned columns, separator lines for readability in terminal
- **Avoid silent operations:** if a function does work but prints nothing, add at minimum a one-liner summary

Pattern for pipeline stages:
```
[stage] Starting... (input: N items)
[stage] Processing... (progress if slow)
[stage] Done. (output: M items, K dropped, timing)
```

When reviewing existing code, flag silent operations that should have logging — suggest where to add it without implementing unless asked.

### 10. Proactive Suggestions

After completing a task or when context reveals an opportunity, suggest next steps that align with the project's evolution trajectory. Base suggestions on:

**Project trajectory (read MILESTONE.md):**
- The project evolved from basic scraping -> AI ranking -> semantic intelligence -> composite scoring -> pipeline maturity
- Each phase built on the previous one's data and infrastructure
- The pattern: collect raw data -> add intelligence layer -> refine scoring -> improve workflow -> add tracking

**When to suggest:**
- After finishing a feature: "This opens the door to X because we now have Y data"
- When a limitation surfaces: "This could be solved by Z, which fits the Phase N direction"
- When patterns repeat: "We've done this manually 3 times — worth automating as a pipeline stage?"
- When data goes unused: "filtered jobs have score_breakdown but nothing aggregates it yet — market trend analytics?"

**What to suggest (aligned with project vision):**
- New scoring signals or weight adjustments based on observed results
- Analytics over accumulated run data (trends, skill demand shifts, response rates)
- Workflow improvements that reduce manual steps
- Data enrichment that improves downstream quality (e.g., better descriptions -> better semantic scores)
- JSON DBs to persist insights across runs (e.g., company reputation cache, skill frequency tracker)

**How to suggest:**
- Brief, one-liner with the "why now" context
- Tag with the milestone phase it belongs to (existing or "Phase N+1")
- Don't implement unless asked — just surface the idea

### 12. Memory Sync on Commit / Session End

Update the auto-memory file (`/root/.claude/projects/-root-search/memory/MEMORY.md`) whenever:
- **Committing work:** After a `git commit`, update memory with what changed — new features, architectural decisions, config changes, current state
- **Finishing a session:** Before ending a conversation, capture any session-discovered context — gotchas, user corrections, new preferences, state changes
- **What to update:** Current state, new architectural decisions, updated phase/milestone info, newly discovered user preferences
- **What NOT to update:** Temporary debug findings, speculative ideas not yet validated, anything already in CLAUDE.md

### 13. Versioning at Milestones

When a major milestone is completed (new pipeline stage, new scoring system, structural change):
- Suggest creating a git commit with a descriptive message tagging the milestone phase
- Use format: `feat: Phase N — short description` (e.g., `feat: Phase 5 — prepare stage, output runs`)
- After committing, suggest tagging: `git tag vN.0` for major milestones
- Update MILESTONE.md with the commit hash and date
- This creates a navigable history — you can `git diff v4.0..v5.0` to see exactly what a phase changed

**When to trigger:**
- New pipeline stage added (like `prepare`)
- Scoring system changed (like semantic-only → composite)
- Data flow restructured (like flat files → run dirs)
- NOT for small fixes, config tweaks, or doc-only changes

## Tech Stack

- Python 3.13, no framework
- ChromaDB + sentence-transformers (all-MiniLM-L6-v2) for embeddings
- Anthropic Claude API for ranking
- scrapling for HTML scraping (Fetcher, StealthyFetcher)
- Standalone HTML (CDN-loaded libs) for dashboards/visualizations — no JS build toolchain
- rclone for Google Drive sync (`pipeline.py sync`)
- No tests yet — manual validation via pipeline commands

## Data Conventions

### JSON as Database
This project uses JSON files as lightweight databases. When implementing new features that need persistent state, prefer JSON-file storage over external databases:

- **Already in use:** `opportunities.json`, `contacts.json` (trackers), `scraped.json`/`filtered_*.json`/`ranked.json` (per-run data), `.chromadb/` (vector store is the exception)
- **When to add a new JSON DB:** any feature that tracks state across runs — history, analytics, user preferences, caches
- **Where:** persistent state goes in `output/` (gitignored), per-run data goes in `output/runs/{ts}/`
- **Pattern:** load-modify-save with atomic writes, dedup by key field (usually URL or ID)
- **When NOT to use JSON:** high-frequency writes, concurrent access, data > ~50MB — then consider SQLite

## File Layout

```
search/                         # git root
├── CLAUDE.md                   # this file
├── .gitignore
└── job-search/                 # all project code
    ├── scraper/                # 6 job scrapers + config + storage
    ├── ranker/                 # semantic filter + composite score + Claude ranking
    ├── scripts/                # CLI: pipeline.py, trackers
    ├── resumes/                # 8 resume variants (gitignored)
    ├── docs/                   # strategy docs (static reference)
    ├── output/                 # generated data (gitignored)
    │   ├── .chromadb/          # vector store (shared)
    │   ├── runs/               # per-run directories
    │   ├── latest -> runs/ts/  # symlink
    │   ├── opportunities.json  # persistent tracker state
    │   └── contacts.json       # persistent tracker state
    ├── archives/               # old output snapshots
    ├── README.md               # entry point, quick start, structure
    ├── GUIDE.md                # user workflow, commands, examples
    ├── ARCHITECTURE.md         # technical deep-dive, modules, formats
    ├── MILESTONE.md            # project evolution phases
    ├── VECTORDB_BREAKDOWN.md   # embedding/vector DB reference
    └── requirements.txt
```
