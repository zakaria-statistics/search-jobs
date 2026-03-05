# Job Search Workflow — Systematic Find → Apply → Follow → Track

## Overview

This is a repeatable workflow to follow **daily and weekly**. Every step feeds the next. Nothing falls through the cracks if you follow the cadence.

The pipeline has two paths:
- **Automated**: scraper → enrich → Claude ranking → human review → tracker
- **Manual**: LinkedIn/APEC/career pages → human finds job → tracker

Both feed into the same opportunity tracker.

---

## Python Environment

Before running any command, activate the virtual environment:

```bash
cd job-search
python3 -m venv .venv          # first time only
source .venv/bin/activate
pip install -r requirements.txt  # first time only

# Index resumes into vector DB (first time only, auto-reindexes on changes)
python scripts/pipeline.py index
```

For every new terminal session:

```bash
cd job-search
source .venv/bin/activate
```

---

## Daily Workflow (1–1.5 hours)

### Step 0: Run Automated Pipeline (10 min)

Run the automated scrape → rank → review pipeline:

```bash
# Full pipeline (scrape → enrich → rank → review)
python scripts/pipeline.py run

# Or run steps individually:
python scripts/pipeline.py scrape                          # Scrape all sources
python scripts/pipeline.py scrape --sources remoteok arbeitnow wttj  # API sources only (fast)
python scripts/pipeline.py enrich                          # Fetch full Indeed descriptions (top 50)
python scripts/pipeline.py enrich --max-enrich 10          # Limit enrichment count
python scripts/pipeline.py index                           # Index resumes into ChromaDB
python scripts/pipeline.py index --force                   # Force reindex after resume edits
python scripts/pipeline.py rank                            # Semantic filter + Claude ranking
python scripts/pipeline.py review                          # Review ranked jobs interactively
```

> The `rank` command auto-indexes resumes on first run. Use `index --force` after editing resumes.

During review, for each job you can:
- `[a]pprove` → imports to tracker automatically
- `[s]kip` → move to next
- `[v]iew` → see full details and resume tweaks
- `[q]uit` → stop review

Check pipeline health anytime:
```bash
python scripts/pipeline.py status
```

**Scraping cadence:**

| Day | Automated sources | Manual platforms |
|-----|------------------|-----------------|
| Mon | All scrapers (`pipeline.py run`) | LinkedIn alerts |
| Tue | API only (`--sources remoteok arbeitnow`) | WTTJ, Indeed |
| Wed | API only | Company career pages (3 companies), APEC |
| Thu | All scrapers | LinkedIn alerts |
| Fri | API only | StepStone / Randstad (EU), Morocco platforms |

### Step 1: Check Follow-ups Due (5 min)

```bash
python scripts/opportunity_tracker.py due
python scripts/contact_pipeline.py due
```

Act on anything due **before** searching for new roles. Follow up > new applications.

### Step 2: Search for New Opportunities (20 min)

Run the search script or manually check today's platforms per the cadence:

```bash
./scripts/job_search_queries.sh        # print all search URLs
./scripts/job_search_queries.sh --open  # open in browser
```

**Daily platform rotation:**

| Day | Primary platforms | Secondary |
|-----|------------------|-----------|
| Mon | LinkedIn alerts | Free-Work |
| Tue | WTTJ | Indeed |
| Wed | Company career pages (3 companies) | APEC |
| Thu | LinkedIn alerts | Free-Work |
| Fri | StepStone / Randstad (EU) | Morocco platforms |

### Step 3: Evaluate & Log (10 min)

For each interesting role found:

1. Read the full job description
2. Score fit (stack match, location, contract, seniority)
3. Log it:

```bash
python scripts/opportunity_tracker.py add
```

**Quick fit scoring:**
- 4/4 match (role + stack + location + contract) → Apply immediately
- 3/4 match → Apply within 2 days
- 2/4 match → Save, apply if pipeline is thin
- 1/4 or less → Skip

### Step 4: Apply (20 min)

For each role to apply to:

1. Tailor CV headline/summary to match the job title and top 3 requirements
2. Write a short cover note (3–4 sentences max, not a full letter)
3. Submit application
4. Update tracker:

```bash
python scripts/opportunity_tracker.py update
# Set status to "Applied"
```

**Cover note template:**
```
Bonjour,

Ingénieur DevOps avec [X] ans d'expérience sur AWS, Azure, Kubernetes et
Terraform, je suis très intéressé par le poste de [ROLE] chez [COMPANY].

Mon expérience en [KEY MATCH 1] et [KEY MATCH 2] correspond directement
à vos besoins. Bilingue français/anglais, disponible en [CDI/freelance].

Cordialement,
[Nom]
```

### Step 5: Recruiter Outreach (15 min)

Send **2–3 new messages** per day to recruiters/tech leads at target companies.

```bash
python scripts/contact_pipeline.py add     # log the contact
python scripts/contact_pipeline.py update  # mark as "Sent" after messaging
```

Use templates from `docs/05_recruiter_contacts.md`.

### Step 6: Engage on LinkedIn (10 min)

- Comment on 2–3 posts from DevOps/Cloud professionals
- Like/share relevant content from target companies
- Post 1x/week (technical tip, project showcase, or career update)

---

## Weekly Review (Sunday, 30 min)

### Step 7: Review Stats

```bash
python scripts/opportunity_tracker.py stats
python scripts/contact_pipeline.py stats
```

### Step 8: Export & Analyze

```bash
python scripts/opportunity_tracker.py export
python scripts/contact_pipeline.py export
```

Check `output/opportunities_export.md` and `output/contacts_export.md`.

### Step 9: Fill Weekly Review

Open `docs/06_90_day_plan.md` and fill the Weekly Review Template:

1. Applications this week: ___
2. Interviews this week: ___
3. Top 3 active leads: ___
4. What worked: ___
5. What didn't work: ___
6. Adjustments for next week: ___
7. Pipeline health: ___
8. Energy check (1–5): ___

### Step 10: Plan Next Week

- Identify which company career pages to check (rotate 3/week)
- Identify which recruiters to contact
- Prepare for any upcoming interviews
- Update keywords if getting low response rates

---

## Interview Pipeline Workflow

When you get a response:

```
New → Applied → Screening → Interview → Technical → Offer → Accepted
                                                          → Rejected
                                                  → Withdrawn
```

### At Each Stage

| Stage | Action | Follow-up |
|-------|--------|-----------|
| **Screening** | Prepare elevator pitch (2 min), salary expectations | Thank-you email same day |
| **Interview** | Research company (30 min), prepare 5 STAR stories | Thank-you email within 24h |
| **Technical** | Practice: K8s scenarios, Terraform live, CI/CD design, system design | Ask for feedback if rejected |
| **Offer** | Compare with other active pipelines, negotiate | Request 3–5 days to decide |

### Technical Interview Prep Checklist

- [ ] Kubernetes: deploy, scale, troubleshoot a pod/service/ingress
- [ ] Terraform: write a module from scratch, state management, workspaces
- [ ] CI/CD: design a pipeline for a microservice (build → test → scan → deploy)
- [ ] Docker: multi-stage build, security best practices
- [ ] Monitoring: design an observability stack (metrics, logs, traces)
- [ ] Incident: walk through an incident response scenario
- [ ] Security: secret management, image scanning, network policies
- [ ] System design: design a deployment platform for 50 microservices

---

## Tracking Cadence Summary

| What | How often | Tool |
|------|-----------|------|
| Index resumes | Once + after edits | `pipeline.py index` (auto on first `rank`) |
| Automated scrape + rank | Daily or 3x/week | `pipeline.py run` or `scrape` + `rank` |
| Review ranked jobs | After each rank | `pipeline.py review` |
| Search manually | Daily (1 platform/day) | `job_search_queries.sh` |
| Apply to roles | Daily (1–3 per day) | `opportunity_tracker.py add/update` |
| Recruiter outreach | Daily (2–3 messages) | `contact_pipeline.py add/update` |
| Follow up on applications | Every 3–5 days after applying | `opportunity_tracker.py due` |
| Follow up on contacts | Day 3, 7, 14 after first message | `contact_pipeline.py due` |
| Pipeline health check | Daily | `pipeline.py status` |
| Review stats | Weekly (Sunday) | `*_tracker.py stats` |
| Export reports | Weekly | `*_tracker.py export` |
| Update 90-day plan | Weekly | Edit `docs/06_90_day_plan.md` |
| LinkedIn engagement | Daily (10 min) | Manual |
| LinkedIn post | Weekly (Saturday) | Manual |

---

## File Structure

```
job-search/
├── WORKFLOW.md              ← You are here
├── requirements.txt         — Python dependencies
├── scraper/                 — Automated job scrapers
│   ├── __init__.py
│   ├── base.py              — BaseScraper abstract class
│   ├── config.py            — Keywords, regions, match_job() with 5-tier matching
│   ├── description_utils.py — extract_skill_sentences(), count_skill_matches()
│   ├── models.py            — Job dataclass
│   ├── storage.py           — Save/merge scraped jobs
│   ├── indeed.py            — Indeed scraper (StealthyFetcher) + enrich()
│   ├── remoteok.py          — RemoteOK API (lenient matching)
│   ├── arbeitnow.py         — Arbeitnow API (lenient matching, 15 pages)
│   ├── rekrute.py           — Rekrute.com scraper (Morocco)
│   └── wttj.py              — WTTJ via Algolia API (lenient matching)
├── ranker/                  — Semantic filtering + Claude-powered ranking
│   ├── __init__.py
│   ├── config.py            — Candidate context, skill keywords, Claude & semantic settings
│   ├── prompts.py           — System prompt for job scoring (RAG-aware)
│   ├── rank.py              — Filter, slim, rank with Claude, save
│   ├── vectorstore.py       — ChromaDB: index resumes, query by job text
│   └── semantic_filter.py   — Semantic pre-filter using resume embeddings
├── resumes/                 — 6 resume variants (AI/AWS/Azure x EN/FR)
│   └── */main.md            — Stack-specific resume markdown
├── scripts/
│   ├── pipeline.py          — Unified CLI: scrape → index → rank → review → track
│   ├── job_search_queries.sh     — Open all search URLs
│   ├── opportunity_tracker.py    — Track applications (add/list/update/stats/export/due/import)
│   └── contact_pipeline.py       — Track contacts (add/list/update/stats/export/due)
├── docs/
│   ├── 01_candidate_target.md    — Your profile & positioning
│   ├── 02_company_goals.md       — Company research by sector
│   ├── 03_opportunities_map.md   — Platforms, URLs, search keywords
│   ├── 04_job_platforms.md       — Platform strategy & cadence
│   ├── 05_recruiter_contacts.md  — Outreach templates & follow-up rules
│   └── 06_90_day_plan.md         — 12-week execution plan with KPIs
└── output/
    ├── .chromadb/                — Vector store (auto-created, gitignored)
    ├── scraped_YYYY-MM-DD.json   — Daily scraped jobs (auto-created)
    ├── ranked_YYYY-MM-DD.json    — Daily ranked jobs (auto-created)
    ├── opportunities.json        — Application data (auto-created)
    ├── contacts.json             — Contact data (auto-created)
    ├── opportunities_export.md   — Weekly export
    └── contacts_export.md        — Weekly export
```

---

## Quick Start (Day 1)

```bash
cd job-search
source .venv/bin/activate

# 1. Index your resumes (one-time setup)
python scripts/pipeline.py index

# 2. Read your positioning
cat docs/01_candidate_target.md

# 3. Run search queries
./scripts/job_search_queries.sh

# 4. Add your first opportunities
python scripts/opportunity_tracker.py add

# 5. Add your first contacts
python scripts/contact_pipeline.py add

# 6. Check what's due tomorrow
python scripts/opportunity_tracker.py due
python scripts/contact_pipeline.py due
```

Repeat daily. Review weekly. Adjust monthly.

---

## Resume Update Workflow

When you edit a resume variant under `resumes/`:

```bash
# After editing any resumes/*.md file
python scripts/pipeline.py index --force   # Reindex into ChromaDB

# Verify chunks were updated
python scripts/pipeline.py index           # Should say "up-to-date" if no further changes
```

The system detects resume changes via MD5 hashing. The next `rank` command also auto-reindexes if it detects changes, so `index --force` is only needed if you want to verify immediately.
