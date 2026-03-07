# Guide

## 1. Setup

```bash
cd job-search
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure API keys in .env
# ANTHROPIC_API_KEY=sk-ant-...
# HF_API_TOKEN=hf_...   (optional, fallback if sentence-transformers unavailable)

# Index resumes into ChromaDB (one-time, ~3 seconds)
python scripts/pipeline.py index
```

Every new terminal session:

```bash
cd job-search && source .venv/bin/activate
```

---

## 2. Daily Workflow

### Step 1: Scrape (2-5 min)

```bash
python scripts/pipeline.py scrape                                    # all 5 sources
python scripts/pipeline.py scrape --sources remoteok arbeitnow wttj  # API only (fast)
```

### Step 2: Enrich Indeed descriptions (optional, ~2 min)

```bash
python scripts/pipeline.py enrich              # top 50 Indeed jobs
python scripts/pipeline.py enrich --max-enrich 10
```

### Step 3: Filter -- semantic pre-screen (5-15 sec, no API cost)

```bash
python scripts/pipeline.py filter                  # default threshold 0.65
python scripts/pipeline.py filter --threshold 0.7  # stricter
```

### Step 4: Validate -- check for closed/expired postings (1-10 min, no API cost)

```bash
python scripts/pipeline.py validate                    # auto-uses latest filtered file
python scripts/pipeline.py validate --max-validate 50  # check fewer URLs (faster)
python scripts/pipeline.py validate --recheck          # re-check previously checked URLs
```

Drops dead postings before spending Claude API tokens. Saves `validated.json` (live) and `closed.json` (dropped) in the run directory.

### Step 5: Prepare -- inspect what Claude will receive (instant, no API cost)

```bash
python scripts/pipeline.py prepare                       # auto-uses validated.json (or filtered)
```

Check `output/latest/prepared.json` — this is exactly what gets sent to Claude. Adjust if needed.

### Step 6: Rank -- Claude AI scoring (~1-4 min depending on job count)

```bash
python scripts/pipeline.py rank                          # auto-uses prepared.json
python scripts/pipeline.py rank --role "Platform Engineer"
```

Auto-batches into groups of 30 jobs per API call. 67 jobs = 3 batches, streamed with progress feedback. Results are merged and re-ranked globally.

### Step 7: Review -- human-in-the-loop (5-15 min)

```bash
python scripts/pipeline.py review
```

Actions per job: `[a]pprove` (imports to tracker), `[s]kip`, `[v]iew` full details, `[c]heck url` (quick liveness re-check), `[q]uit`.

### Step 8: Follow-ups and outreach

```bash
python scripts/opportunity_tracker.py due   # application follow-ups
python scripts/contact_pipeline.py due      # recruiter follow-ups
```

Act on follow-ups before searching for new roles.

### Full pipeline shortcut

```bash
python scripts/pipeline.py run                 # scrape + enrich + filter + validate + prepare + rank + review
python scripts/pipeline.py run --skip-validate # skip URL validation (faster)
```

---

## 3. Command Reference

### pipeline.py

| Command | Description | Time |
|---------|-------------|------|
| `scrape` | Run all or selected scrapers | 2-5 min |
| `scrape --sources remoteok arbeitnow wttj` | API sources only | ~30 sec |
| `scrape --keywords "SRE" "Cloud Engineer" --regions france netherlands --max-pages 1` | Targeted scrape | ~1 min |
| `enrich` | Fetch full Indeed descriptions (top 50) | ~8 min |
| `enrich --max-enrich 10` | Limit enrichment count | ~2 min |
| `index` | Index resumes into ChromaDB (skips if unchanged) | ~3 sec |
| `index --force` | Force reindex after resume edits | ~3 sec |
| `filter` | Semantic pre-filter, saves `filtered_*.json` | 5-15 sec |
| `filter --threshold 0.7` | Stricter similarity threshold | 5-15 sec |
| `filter --file output/scraped_*.json` | Filter a specific file | 5-15 sec |
| `validate` | Check URLs for closed/expired postings | 1-10 min |
| `validate --max-validate 50` | Limit URLs to check | 1-3 min |
| `validate --recheck` | Re-check previously checked URLs | 1-10 min |
| `prepare` | Slim jobs for Claude — inspect before ranking | instant |
| `prepare --file output/filtered_*.json` | Prepare a specific file | instant |
| `rank` | Claude scoring (auto-uses `prepared.json`) | ~30 sec |
| `rank --file output/filtered_*.json` | Rank a specific file | ~30 sec |
| `rank --role "Platform Engineer"` | Focus ranking on a role | ~30 sec |
| `review` | Interactive review of ranked jobs | 5-15 min |
| `run` | Full chain: scrape + enrich + filter + validate + prepare + rank + review | ~25 min |
| `run --skip-validate` | Skip URL validation stage | ~20 min |
| `manual` | Add a job manually to tracker | ~1 min |
| `status` | Pipeline health and statistics | instant |

Example `status` output:

```
==================================================
  PIPELINE STATUS
==================================================
  Scraped files: 5
  Latest: scraped_2026-03-03.json
  Total jobs (last 5 files): 342

  Ranked files: 5
  Latest: ranked_2026-03-03.json

  Tracked opportunities: 15
    New: 5  Applied: 6  Interview: 1  Rejected: 2
  Tracked contacts: 8
==================================================
```

### opportunity_tracker.py

| Command | Description |
|---------|-------------|
| `add` | Add a new opportunity interactively |
| `list` | List all opportunities grouped by status |
| `update` | Update status (auto-sets follow-up 5 days after applying) |
| `stats` | Distribution by status, source, company; response rate |
| `export` | Generate Markdown table to `output/opportunities_export.md` |
| `due` | Show follow-ups due today |
| `import` | Bulk import from ranked JSON files (deduplicates by URL) |

### contact_pipeline.py

| Command | Description |
|---------|-------------|
| `add` | Add recruiter/tech lead with platform info |
| `list` | List contacts grouped by outreach status |
| `update` | Update status with auto-scheduled follow-ups |
| `stats` | Response rates by status and type |
| `export` | Generate Markdown export |
| `due` | Show follow-ups due today |

---

## 4. Application Tracking

### Add

```bash
python scripts/opportunity_tracker.py add
```

```
Company: Capgemini
Role: Cloud DevOps Engineer
Location: Paris, France
Source (LinkedIn/WTTJ/Indeed/career page/referral/other): LinkedIn
Job URL: https://linkedin.com/jobs/view/12345
Notes: Python-heavy stack

Added #3: Cloud DevOps Engineer at Capgemini
```

### List

```bash
python scripts/opportunity_tracker.py list
```

```
  NEW (3)
  # 1  Sopra Steria    Senior DevOps Engineer    Paris, France
  # 2  ING Bank        Cloud Platform Engineer   Amsterdam

  APPLIED (2)
  # 4  BNP Paribas     DevOps Engineer           Paris, France
       Follow-up: 2026-03-08
```

### Update

```bash
python scripts/opportunity_tracker.py update
```

```
Opportunity ID to update: 1
New status (number): 1   # Applied
  Applied date set. Follow-up scheduled for 2026-03-08
```

### Due, stats, import, export

```bash
python scripts/opportunity_tracker.py due      # follow-ups due today
python scripts/opportunity_tracker.py stats    # distribution + response rate
python scripts/opportunity_tracker.py import   # bulk import from ranked_*.json
python scripts/opportunity_tracker.py export   # Markdown table to output/
```

### Status flow

```
New -> Applied -> Screening -> Interview -> Technical -> Offer -> Accepted
                                                              -> Rejected
                                                       -> Withdrawn
```

---

## 5. Contact Pipeline

### Add

```bash
python scripts/contact_pipeline.py add
```

```
Contact type: 0 (Recruiter)
Name: Marie Dupont
Company: Sopra Steria
Platform: LinkedIn
Profile URL: https://linkedin.com/in/marie-dupont
```

### Update with auto follow-up cadence

```bash
python scripts/contact_pipeline.py update
```

Cadence: Day 0 (sent) -> Day 3 (follow-up #1) -> Day 10 (follow-up #2) -> pause.

### Due, stats, export

```bash
python scripts/contact_pipeline.py due      # follow-ups due today
python scripts/contact_pipeline.py stats    # response rates by status and type
python scripts/contact_pipeline.py export   # Markdown export
```

---

## 6. Weekly Review (Sunday, 30 min)

1. Run stats and export:

```bash
python scripts/opportunity_tracker.py stats
python scripts/opportunity_tracker.py export
python scripts/contact_pipeline.py stats
python scripts/contact_pipeline.py export
```

2. Fill the Weekly Review Template in `docs/06_90_day_plan.md`:
   - Applications this week
   - Interviews this week
   - Top 3 active leads
   - What worked / what didn't
   - Adjustments for next week
   - Energy check (1-5)

3. Plan next week:
   - Which company career pages to check (rotate 3/week)
   - Which recruiters to contact
   - Prepare for upcoming interviews
   - Update keywords if response rates are low

---

## 7. Interview Pipeline

### Stages

| Stage | Action | Follow-up |
|-------|--------|-----------|
| Screening | Elevator pitch (2 min), salary expectations | Thank-you email same day |
| Interview | Research company (30 min), 5 STAR stories | Thank-you email within 24h |
| Technical | K8s scenarios, Terraform live, CI/CD design, system design | Ask for feedback if rejected |
| Offer | Compare with active pipelines, negotiate | Request 3-5 days to decide |

### Technical Prep Checklist

- Kubernetes: deploy, scale, troubleshoot pod/service/ingress
- Terraform: write a module from scratch, state management, workspaces
- CI/CD: design a pipeline (build -> test -> scan -> deploy)
- Docker: multi-stage build, security best practices
- Monitoring: design observability stack (metrics, logs, traces)
- Incident: walk through an incident response scenario
- Security: secret management, image scanning, network policies
- System design: deployment platform for 50 microservices

---

## 8. Tips

### Scraping cadence

| Day | Command | Time |
|-----|---------|------|
| Mon | `pipeline.py scrape` (all sources) | ~5 min |
| Tue | `scrape --sources remoteok arbeitnow rekrute wttj` | ~30 sec |
| Wed | `scrape --sources remoteok arbeitnow rekrute wttj` | ~30 sec |
| Thu | `pipeline.py scrape` (all sources) | ~5 min |
| Fri | `scrape --sources remoteok arbeitnow rekrute wttj` | ~30 sec |

### Speed tips

- Skip Indeed entirely with `--sources remoteok arbeitnow rekrute wttj` (~30 sec vs ~5 min)
- Limit Indeed regions: `--regions france netherlands` (2 domains vs 9)
- Fewer keywords: `--keywords "DevOps Engineer" "Cloud Engineer"` (cuts page loads ~60%)
- Reduce pages: `--max-pages 1` (newest listings only)
- Combine: `--regions france --keywords "DevOps Engineer" --max-pages 1` (~1 min total)

### Resume update workflow

```bash
# After editing any resumes/*/main.md file:
python scripts/pipeline.py index --force   # reindex into ChromaDB
python scripts/pipeline.py index           # verify: should say "up-to-date"
```

The system auto-detects changes via MD5 hashing. The next `filter` also auto-reindexes if needed.
