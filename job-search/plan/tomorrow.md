# Tomorrow's Plan — Phase 8: Intelligence Foundation + Ghost Detection

**Date:** 2026-03-09
**Goal:** Build the foundation that makes every future run smarter, and ship ghost detection as the first prediction feature.
**Grade:** G4 — new pipeline stage, new DB, new module

---

## Architecture — Phase 8 Overview

### Pipeline Flow (before → after)

```
BEFORE (Phase 7):
  scrape → enrich → filter → validate → prepare → rank → review
    │                                      │                 │
    ▼                                      ▼                 ▼
  scraped.json                        validated.json    opportunities.json

AFTER (Phase 8):
  scrape ──→ enrich → filter → validate → ANALYZE → prepare → rank → review
    │                                        │                          │
    │    ┌───────────────────────────────────┘                          │
    ▼    ▼                                                              ▼
  record_to_db()                                                  opportunities.json
    │    │
    │    ├─ ghost_score per job
    │    ├─ blockers[] per job
    │    ├─ company intel (Glassdoor)
    │    └─► analyzed.json + terminal tiers
    │
    └─► intelligence.db (persistent, grows every run)
```

### Module Map

```
scraper/                          ranker/                         scripts/
  base.py (ABC)                     intelligence_db.py [NEW]        pipeline.py
  config.py                         ghost_detector.py  [NEW]          + cmd_analyze
  models.py                         offer_intelligence.py [NEW]       + record_to_db hook
  linkedin.py                       semantic_filter.py
  glassdoor.py [NEW]                composite_score.py              output/
  indeed.py                         rank.py                           intelligence.db [NEW]
  remoteok.py                       config.py                         runs/{ts}/
  arbeitnow.py                      prompts.py                          analyzed.json [NEW]
  wttj.py                                                              scraped.json
  rekrute.py                                                           filtered_*.json
  url_validator.py                                                     validated.json
  storage.py
```

### Dependency Direction

```
                        ┌──────────────────────────────────┐
                        │         pipeline.py              │
                        │  (orchestrator, all cmd_*())     │
                        └──┬────┬────┬────┬────┬───────────┘
                           │    │    │    │    │
              ┌────────────┘    │    │    │    └──────────────────┐
              ▼                 ▼    │    ▼                      ▼
        scraper/*          ranker/   │  ranker/            ranker/
        (scrape)          semantic   │  rank.py           offer_intelligence.py
                         _filter.py  │    │                  │        │
              │               │      │    │                  │        │
              ▼               ▼      │    ▼                  ▼        ▼
         glassdoor.py   composite    │  config.py      ghost_        intelligence
         [NEW]          _score.py    │  prompts.py     detector.py   _db.py [NEW]
              │               │      │                 [NEW]              │
              │               ▼      │                   │               │
              │          config.py   │                   ▼               ▼
              │          (weights)   │              intelligence.db   intelligence.db
              │                      │              (read: history)   (write: record)
              └──────────────────────┘
                    │
                    ▼
              intelligence.db
              (write: company_reviews)
```

### Data Flow — Analyze Stage Detail

```
                    validated.json
                         │
                         ▼
              ┌─────────────────────┐
              │   ANALYZE STAGE     │
              │                     │
              │  For each job:      │
              │                     │
              │  ┌────────────────┐ │      ┌──────────────────┐
              │  │ Ghost Detector │◄├──────►│  intelligence.db │
              │  │                │ │       │                  │
              │  │ • posting age  │ │       │  offers table    │
              │  │ • repost freq  │ │       │  (seen_count,    │
              │  │ • employer type│ │       │   first_seen,    │
              │  │ • desc quality │ │       │   sources)       │
              │  │ • multi-source │ │       │                  │
              │  └───────┬────────┘ │       │  company_reviews │
              │          │          │       │  (rating,        │
              │          ▼          │       │   interview,     │
              │  ┌────────────────┐ │       │   salary)        │
              │  │ Blocker Filter │ │       └──────────────────┘
              │  │                │ │
              │  │ • visa         │ │
              │  │ • language     │ │
              │  │ • clearance    │ │
              │  │ • seniority    │ │
              │  └───────┬────────┘ │
              │          │          │
              │          ▼          │
              │  ┌────────────────┐ │
              │  │ Tier Classifier│ │
              │  │                │ │
              │  │ ghost + block  │ │
              │  │ + fit_score    │ │
              │  │      │         │ │
              │  │      ▼         │ │
              │  │ APPLY NOW     │ │
              │  │ WORTH EFFORT  │ │
              │  │ LONG SHOT     │ │
              │  │ SKIP          │ │
              │  └───────┬────────┘ │
              └──────────┼──────────┘
                         │
                         ▼
                  analyzed.json
                  + terminal report
```

### SQLite Schema (intelligence.db)

```
┌─────────────────────┐       ┌──────────────────────┐
│       offers        │       │        runs          │
├─────────────────────┤       ├──────────────────────┤
│ fingerprint PK      │       │ run_id PK            │
│ title               │       │ scraped_at           │
│ company             │       │ total_jobs           │
│ first_seen          │       │ sources (JSON)       │
│ last_seen           │       └──────────┬───────────┘
│ seen_count          │                  │
│ sources (JSON)      │                  │
│ urls (JSON)         │       ┌──────────┴───────────┐
│ employer_type       │       │  offer_sightings     │
│ ghost_score         │       ├──────────────────────┤
└────────┬────────────┘       │ id PK                │
         │                    │ fingerprint FK ───────┤
         │                    │ run_id FK             │
         │                    │ url                   │
         │                    │ source                │
         └────────────────────│ date_posted           │
                              │ description_length    │
                              │ location              │
                              └──────────────────────┘

┌─────────────────────────┐
│    company_reviews      │
├─────────────────────────┤
│ company_name PK         │
│ glassdoor_url           │
│ overall_rating          │
│ review_count            │
│ recommend_pct           │
│ ceo_approval_pct        │
│ interview_difficulty    │
│ interview_positive_pct  │
│ salary_data (JSON)      │
│ company_size            │
│ industry                │
│ scraped_at              │
└─────────────────────────┘
```

### Predictive Model — How Scores Are Computed

```
INPUT: one job + its history from intelligence.db + company review (if cached)

═══════════════════════════════════════════════════════════════════
  GHOST SCORE (0.0 = real ──── 1.0 = ghost)
═══════════════════════════════════════════════════════════════════

  Signal               Weight    How it's computed
  ──────────────────── ──────    ─────────────────────────────────
  posting_age          × 0.25    0–14d→0.0  15–30d→0.3  31–60d→0.6  60+→1.0
  repost_frequency     × 0.25    seen_count / observation_window (normalized)
  employer_type        × 0.20    direct→0.1  consultancy→0.5  agency→0.8
  description_quality  × 0.15    empty→0.9  <100ch→0.6  100–500→0.3  500+→0.1
  company_intel        × 0.15    no glassdoor→0.5  rating<3→0.4  has reviews→0.1

  ghost_score = Σ(signal × weight)

  CORE (5 signals — from domain knowledge):
  Signal               Weight    Source
  ──────────────────── ──────    ──────────────────────────────
  posting_age          × 0.15    date_posted field
  repost_frequency     × 0.15    intelligence.db seen_count
  employer_type        × 0.15    company name regex
  description_quality  × 0.10    description text analysis
  company_intel        × 0.10    Glassdoor reviews (cached)

  RESEARCH-BACKED (4 signals — from 2025–2026 ghost job studies):
  Signal               Weight    Source
  ──────────────────── ──────    ──────────────────────────────
  pipeline_language    × 0.10    "talent community", "always looking" in desc
  careers_page_match   × 0.10    HTTP check: is job on company's own site?
  description_hash     × 0.10    same text across runs but date refreshed?
  contact_present      × 0.05    named recruiter/hiring manager in listing?

  Total weights = 1.00

  Example:
    DevSecOps @ MY Humancapital GmbH
    age=0.3×0.15 + repost=0.95×0.15 + agency=0.8×0.15
    + desc=0.3×0.10 + company=0.5×0.10
    + pipeline=0.2×0.10 + no_careers=0.7×0.10 + same_hash=0.8×0.10 + no_contact=0.6×0.05
    = 0.045 + 0.1425 + 0.12 + 0.03 + 0.05 + 0.02 + 0.07 + 0.08 + 0.03
    = 0.587 → UNCERTAIN (but trending ghost, and agency override may push to SKIP)

═══════════════════════════════════════════════════════════════════
  BLOCKER PENALTY (1.0 = no blockers ──── 0.0 = impossible)
═══════════════════════════════════════════════════════════════════

  Start at 1.0, multiply penalties:

  Blocker type         Severity    Penalty
  ──────────────────── ─────────── ───────
  visa hard            HARD        × 0.05    (nearly impossible)
  visa uncertain       UNCERTAIN   × 0.70    (unknown, risky)
  language required    HARD        × 0.05
  language preferred   SOFT        × 0.85
  clearance            HARD        × 0.00    (impossible)
  seniority gap > 5yr  HARD        × 0.30
  seniority gap 3–5yr  SOFT        × 0.70
  location on-site     SOFT        × 0.80    (relocation friction)

  blocker_penalty = 1.0 × penalty₁ × penalty₂ × ...

  Example:
    Job requires "German C1" (HARD) + "on-site Munich" (SOFT)
    = 1.0 × 0.05 × 0.80 = 0.04 → almost blocked

═══════════════════════════════════════════════════════════════════
  OPPORTUNITY SCORE (final ranking metric)
═══════════════════════════════════════════════════════════════════

  opportunity = (1 - ghost_score) × 0.35      "is it real?"
              + blocker_penalty   × 0.30      "can I get it?"
              + composite_score   × 0.35      "does it match me?"

  ┌─────────────────────────────────────────────────────┐
  │  opportunity ≥ 0.65  →  APPLY NOW                  │
  │  opportunity 0.45–0.65 →  WORTH EFFORT             │
  │  opportunity 0.25–0.45 →  LONG SHOT                │
  │  opportunity < 0.25  →  SKIP                       │
  │                                                     │
  │  Override: any HARD blocker → cap at LONG SHOT max  │
  │  Override: ghost_score > 0.80 → force SKIP          │
  └─────────────────────────────────────────────────────┘

  Example — good opportunity:
    DevOps Engineer @ MEMX
    (1 - 0.12) × 0.35 + 1.0 × 0.30 + 0.76 × 0.35
    = 0.308 + 0.30 + 0.266 = 0.874 → APPLY NOW

  Example — ghost:
    DevSecOps @ MY Humancapital GmbH
    (1 - 0.91) × 0.35 + 1.0 × 0.30 + 0.57 × 0.35
    = 0.0315 + 0.30 + 0.1995 = 0.531 → WORTH EFFORT
    BUT ghost_score > 0.80 → override → SKIP

  Example — blocked:
    Cloud Engineer @ Munich Corp (German C1 + on-site)
    (1 - 0.15) × 0.35 + 0.04 × 0.30 + 0.72 × 0.35
    = 0.2975 + 0.012 + 0.252 = 0.5615 → WORTH EFFORT
    BUT has HARD blocker → cap at LONG SHOT
```

### Feedback Loop — Learn From Application Outcomes

```
The ghost detector starts with heuristics (age, reposts, employer type).
But the REAL accuracy comes from tracking what happens AFTER you apply.

                  ┌──────────┐
   analyze ──────►│ PREDICT  │──► "APPLY NOW" / "SKIP"
                  └────┬─────┘
                       │
                       ▼
                  ┌──────────┐
                  │  APPLY   │──► send application
                  └────┬─────┘
                       │
                       ▼
                  ┌──────────┐
                  │ OUTCOME  │──► response / ghosted / rejected / interview
                  └────┬─────┘
                       │
                       ▼
                  ┌──────────┐
                  │  LEARN   │──► feed outcome back into model weights
                  └──────────┘

Outcome tracking (in opportunities.json, already exists):
  applied + response within 14 days    → was REAL
  applied + ghosted after 30 days      → was GHOST (or weak application)
  applied + auto-reject within 1 day   → was GHOST or ATS filtered
  applied + interview                  → was REAL + good fit

Over time: "jobs with ghost_score > 0.7 resulted in 0/12 responses"
  → validates the model
  → tunes weights automatically

Industry reference (2026):
  ~6% of listed jobs are real (source: Code Pulse, Feb 2026 — 3/47 applications)
  Ghost jobs exist to: build talent pipelines, show growth to investors,
  gauge salary expectations, satisfy internal posting requirements.
  Our model targets this exact problem.
```

---

## Session 1 — SQLite Intelligence DB + History Backfill (~45 min)

### 1.1 Create intelligence DB schema

**New file:** `ranker/intelligence_db.py`

```
Tables:

offers
  - fingerprint TEXT PRIMARY KEY    -- "title::company" normalized
  - title TEXT
  - company TEXT
  - first_seen DATE
  - last_seen DATE
  - seen_count INTEGER
  - sources TEXT (JSON array)       -- ["remoteok", "arbeitnow"]
  - urls TEXT (JSON array)          -- all URLs seen
  - run_ids TEXT (JSON array)       -- runs it appeared in
  - employer_type TEXT              -- direct/agency/consultancy (NULL until classified)
  - ghost_score REAL               -- NULL until predicted

runs
  - run_id TEXT PRIMARY KEY         -- "2026-03-06-15-20-10"
  - scraped_at DATETIME
  - total_jobs INTEGER
  - sources TEXT (JSON array)

offer_sightings
  - id INTEGER PRIMARY KEY
  - fingerprint TEXT                -- FK to offers
  - run_id TEXT                     -- FK to runs
  - url TEXT
  - source TEXT
  - date_posted TEXT
  - description_length INTEGER
  - description_hash TEXT           -- SHA256[:16] for zombie detection (signal 8)
  - location TEXT
  - has_contact BOOLEAN             -- named recruiter found? (signal 9)
  - has_pipeline_language BOOLEAN   -- "talent pool" phrases? (signal 6)

careers_page_cache
  - company_name TEXT PRIMARY KEY
  - careers_url TEXT                -- company careers page URL
  - job_found BOOLEAN              -- was the job title found on their site?
  - checked_at DATETIME
  - check_status TEXT               -- success/not_found/no_careers_page/error
```

**Functions:**
- `init_db()` — create tables if not exist
- `record_run(run_id, jobs)` — insert run + upsert all offers + insert sightings
- `get_offer_history(fingerprint)` — full history for one offer
- `get_ghost_candidates(min_seen, min_age_days)` — query for likely ghosts
- `get_company_profile(company)` — aggregate stats per company

**Location:** `output/intelligence.db`

### 1.2 Backfill existing 5 runs

Script: loop through `output/runs/*/scraped.json`, call `record_run()` for each.
Result: 642 jobs indexed, 99 cross-run overlaps immediately queryable.

### 1.3 Hook into pipeline

In `pipeline.py`, after `cmd_scrape` completes, auto-call `record_run()`.
Every future scrape automatically feeds the intelligence DB.

---

## Session 2 — Increase Description Length (~30 min)

### Current state:
- arbeitnow: capped at 500 chars (all 98 jobs)
- remoteok: capped at 500 chars (all 84 jobs)
- linkedin: 0 chars (empty — guest API returns no descriptions)
- wttj: mixed, 160 jobs under 100 chars

### Actions:
- Find the truncation point in each scraper and raise to 3000 chars
- LinkedIn stays empty (API limitation, needs enrichment stage)
- Test with a quick scrape to verify longer descriptions come through

**Why 3000:** enough for blocker detection and specificity scoring. More than that = diminishing returns + storage bloat.

---

## Session 3 — Ghost Prediction Model (~1 hour)

### 3.1 Ghost scoring function

**New file:** `ranker/ghost_detector.py`

```python
def compute_ghost_score(offer_row, sightings, desc_hashes, careers_check) -> float:
    """
    Returns 0.0 (definitely real) to 1.0 (definitely ghost/market study).
    9 signals, research-backed weights.
    """
```

### Signal details (9 signals):

**CORE SIGNALS (from domain knowledge):**

**1. Posting age (weight: 0.15)**
```
age_days = (today - date_posted).days
  0–14 days  → 0.0 (fresh, likely real)
  15–30 days → 0.3
  31–60 days → 0.6  (real jobs fill in 30–45 days — Greenhouse 2025)
  61–90 days → 0.8
  90+ days   → 1.0 (almost certainly ghost)
```

**2. Repost frequency (weight: 0.15)**
```
seen_count across observation window:
  seen 2x in 2 days  → 0.1 (just scraped twice, normal)
  seen 3x in 14 days → 0.4 (starting to look stale)
  seen 5x in 30 days → 0.8 (chronic reposter)
  seen 8x (like MY Humancapital GmbH) → 0.95
```

**3. Employer type (weight: 0.15)**
```
Company name pattern matching:
  "Consulting", "Solutions", "Staffing", "Recruiting" → agency (0.7)
  "GmbH" + "Human" or "Capital" or "Talent"          → agency (0.8)
  Known agencies: Hays, Adecco, Randstad, ManpowerGroup, Robert Half → 0.8
  Direct employer (no patterns match)                  → 0.1
```

**4. Description quality (weight: 0.10)**
```
  empty (0 chars)     → 0.9 (placeholder)
  short (<100 chars)  → 0.6
  medium (100–500)    → 0.3
  rich (500+)         → 0.1
  + specificity bonus: named tech versions, team size, project → -0.1
  + vague penalty: "competitive", "fast-paced", "rockstar"    → +0.1
```

**5. Company intelligence (weight: 0.10)**
```
  No Glassdoor presence at all        → 0.5 (uncertain)
  Glassdoor rating < 3.0              → 0.4 (high churn company)
  Glassdoor rating 3.0–4.0, reviews>50 → 0.2 (normal)
  Glassdoor rating > 4.0, reviews>50  → 0.1 (healthy company)
  Has interview data on Glassdoor     → -0.1 bonus (real hiring process)
```

**RESEARCH-BACKED SIGNALS (from 2025–2026 studies):**

**6. Pipeline language (weight: 0.10)**
```
Regex scan for talent-pool phrases:
  "talent community"                   → 0.9
  "always looking for"                 → 0.9
  "future opportunities"               → 0.8
  "talent pipeline" / "talent pool"    → 0.8
  "proactive sourcing"                 → 0.7
  None found                           → 0.0

Why: 43% of ghost jobs exist to "build talent pipeline" (Clarify Capital)
```

**7. Careers page match (weight: 0.10)**
```
Check if job exists on company's own careers page:
  Found on company site       → 0.0 (confirmed real)
  Not found on company site   → 0.7 (suspicious)
  Company has no careers page → 0.3 (small company, not necessarily ghost)
  Check failed (timeout/error)→ 0.4 (uncertain)

How: GET {company_website}/careers or /jobs, search for job title
Cost: 1 HTTP request per unique company (cached in intelligence.db)
```

**8. Description hash (weight: 0.10)**
```
Hash the description text, compare across runs:
  New description (first time seen)     → 0.0
  Same hash, same date across runs      → 0.1 (normal, just re-scraped)
  Same hash, but date_posted refreshed  → 0.8 (zombie listing — date bumped to look new)
  Different hash (description changed)  → 0.1 (company updated listing, sign of activity)

How: SHA256(normalize(description))[:16] stored in offer_sightings
Why: "Sometimes jobs are reposted to look new; if the job ID is old but
      the date is new, it's a zombie listing" — MintCareer 2026
```

**9. Contact present (weight: 0.05)**
```
Check if listing has a named person:
  Named recruiter/hiring manager in text  → 0.0 (real person = real process)
  "Apply to:" with email                  → 0.1
  Generic "Apply now" button only         → 0.5
  No contact info at all                  → 0.6

Detection: regex for names + titles ("John Smith, Talent Acquisition",
  "Contact: hiring@company.com", "Recruiter: @linkedin.com/in/...")
```

### 3.2 Apply to existing data

- Run ghost scoring on all 509 tracked offers
- Print a report: top 20 most likely ghosts, top 20 most likely real
- Validate manually: do the results make sense?

**Expected easy catches from current data:**
- `MY Humancapital GmbH` — 8x sightings, agency name → high ghost score
- `Odixcity Consulting` — 6x sightings, "Consulting" → ghost
- `Müller's Solutions` — 3x sightings, "Solutions" → suspicious
- LinkedIn empty descriptions → all get description_empty penalty

### 3.3 Integrate into pipeline

New flag: `python scripts/pipeline.py analyze`
- Loads validated/filtered jobs
- Queries intelligence DB for history
- Computes ghost_score per job
- Marks verdict: `LIKELY_GHOST` / `UNCERTAIN` / `LIKELY_REAL`
- Saves `analyzed.json` with ghost intelligence attached
- Prints summary: "12 likely real, 5 uncertain, 6 likely ghost"

---

## Session 4 — Blocker Filter (quick win) (~20 min)

Simple regex filter that tags hard blockers. Not a full prediction model — just catches obvious disqualifiers.

```python
BLOCKERS = {
    "visa": [r"authorized to work", r"no.*sponsorship", r"EU citizens", r"right to work"],
    "language": [r"fluent german", r"deutsch.*erforderlich", r"german.*c[12]", r"native.*french"],
    "clearance": [r"security clearance", r"habilitation", r"classified"],
    "seniority": [r"(\d{2})\+?\s*years", r"minimum (\d+) years"],  # extract number, compare to 5
}
```

Runs as part of the analyze stage. Adds `blockers[]` to each job.

**Effort estimation** (from description, same regex pass):

```python
EFFORT_SIGNALS = {
    "easy_apply":     (r"easy apply|quick apply|one.click", -0.5),
    "cover_letter":   (r"cover letter|lettre de motivation", +2),
    "take_home":      (r"take.home|coding challenge|case study|technical test", +6),
    "portfolio":      (r"portfolio|work samples|examples of", +4),
    "multi_round":    (r"(\d+).*(round|stage|step).*interview", +3),
    "video_intro":    (r"video introduction|video pitch", +2),
}
# base = 1 hour, sum adjustments → effort_hours
```

**Late rejection risk** (from blockers):

```python
LATE_REJECTION_RISK = {
    "visa_uncertain":    0.60,  # most common late-stage killer
    "seniority_gap_3+":  0.40,  # passes screen, fails technical
    "language_soft":     0.30,  # might pass screen, fail interview
    "location_reloc":    0.20,  # discussed late in process
}
# time_risk = effort_hours × P(late_rejection)
```

**Effort-risk labels** (added to each job):

```
QUICK WIN        — effort < 2hrs, time_risk < 1.0   → "apply today"
WORTH INVESTING  — effort > 2hrs, time_risk < 3.0   → "prepare this week"
LOTTERY TICKET   — effort < 2hrs, time_risk 1-5     → "quick apply, don't over-invest"
TIME TRAP        — effort > 2hrs, time_risk > 5.0   → "⚠ skip unless dream job"
```

---

## Session 5 — Wire It All Together (~30 min)

### Updated pipeline flow:

```
scrape → record_to_db → enrich → filter → validate → ANALYZE → prepare → rank → review
                                                         │
                                              ghost_score + blockers + time_risk
                                              → analyzed.json
                                              → terminal summary with tiers
```

### Terminal output after analyze:

```
═══════════════════════════════════════════════════════════════════════
  OFFER INTELLIGENCE REPORT
═══════════════════════════════════════════════════════════════════════
  Total analyzed:  24
  Likely real:     12  ██████████████
  Uncertain:        5  ██████
  Likely ghost:     7  ████████

  Hard blockers: 3 visa, 2 language, 1 clearance

  ── QUICK WINS (apply today, <1hr each) ─────────────────────────────
    1. DevOps Engineer @ MEMX           opp=0.87  ~0.5hr  risk=LOW
       easy apply, no blockers, fresh (5d)
    2. Senior Cloud Engineer @ Kunai    opp=0.72  ~1hr    risk=LOW
       direct employer, strong skill match

  ── WORTH INVESTING (prepare this week) ─────────────────────────────
    3. Platform Eng @ CEF AI            opp=0.68  ~4hrs   risk=LOW
       has take-home test, but no blockers, startup (real need)

  ── LOTTERY TICKETS (quick apply, don't over-invest) ────────────────
    4. SRE @ BigCorp                    opp=0.45  ~0.5hr  risk=MOD
       visa uncertain, but easy apply — worth the 30 min

  ── ⚠ TIME TRAPS (skip unless dream job) ────────────────────────────
    5. DevOps @ MunichCorp              opp=0.52  ~8hrs   risk=HIGH
       4-round process + German C1 soft blocker
       → likely rejected at interview stage for language

  ── SKIP (ghost / blocked) ──────────────────────────────────────────
    - DevSecOps @ MY Humancapital GmbH  ghost=0.91  (agency, 8x repost)
    - Devops Annotator @ Odixcity       ghost=0.85  (consulting, 6x repost)
    - Cloud Eng @ SecureCorp            BLOCKED: security clearance required
═══════════════════════════════════════════════
```

---

## Session 6 — Glassdoor Company Intelligence Scraper (~1.5 hours)

### What we scrape

NOT job listings (we have enough sources). Instead, scrape **company review data** to enrich the intelligence DB.

For each company seen in our offers:

```
Glassdoor company page → extract:
  - overall_rating (1.0–5.0)
  - review_count
  - recommend_to_friend_pct
  - ceo_approval_pct
  - interview_difficulty (1.0–5.0)
  - interview_experience (positive/neutral/negative %)
  - salary_ranges (for matching roles if available)
  - company_size
  - industry
  - founded_year
```

### Why this matters for prediction

| Signal | How it helps |
|--------|-------------|
| Low rating (<3.0) + many reviews | Company has real problems — apply with caution |
| High rating + few reviews | Might be fake reviews — uncertain |
| High interview difficulty | Prepare harder, but job is likely real (they invest in process) |
| No Glassdoor presence | Small/new company — not a bad sign, just less data |
| High recommend % + active hiring | Real growth, good signal |
| Salary data exists | Can validate if offer is market-rate or lowball |

### Implementation

**New file:** `scraper/glassdoor.py`

```
class GlassdoorScraper:
    """Scrapes company reviews from Glassdoor. NOT a job scraper."""

    def scrape_company(self, company_name: str) -> dict | None:
        """Search Glassdoor for company, return review data."""

    def scrape_companies(self, company_names: list[str]) -> dict[str, dict]:
        """Batch scrape. Returns {company_name: review_data}."""
```

**Approach — 2 options:**

1. **Glassdoor API (unofficial)** — some endpoints still work with the right headers
   - Pro: structured data, fast
   - Con: may break, rate-limited

2. **HTML scraping via DataImpulse proxy** — use residential proxy like LinkedIn scraper
   - Pro: reliable, same infra as LinkedIn
   - Con: slower, more bandwidth, needs HTML parsing

Start with option 2 (proxy + HTML), same pattern as `linkedin.py`:
- DataImpulse residential proxy for anti-bot bypass
- Byte budget tracking (reuse `_ByteRateLimiter` pattern)
- Rate limiting between requests

### Anti-bot handling

Glassdoor is aggressive with bot detection:
- Requires cookies/session from initial page load
- May need `StealthyFetcher` (headless browser) for first visit
- Subsequent API calls can use session cookies
- DataImpulse residential IPs help avoid IP bans

### Integration with intelligence DB

New table in `intelligence.db`:

```sql
company_reviews
  - company_name TEXT PRIMARY KEY
  - glassdoor_url TEXT
  - overall_rating REAL
  - review_count INTEGER
  - recommend_pct REAL
  - ceo_approval_pct REAL
  - interview_difficulty REAL
  - interview_positive_pct REAL
  - salary_data TEXT (JSON)
  - company_size TEXT
  - industry TEXT
  - scraped_at DATETIME
```

### Pipeline integration

Two modes:
1. **On-demand:** `python scripts/pipeline.py glassdoor --company "MEMX"`
2. **Batch (during analyze):** For all companies in current run that don't have reviews cached yet

```
analyze stage:
  1. Get list of unique companies from validated jobs
  2. Check intelligence.db — which companies missing review data?
  3. Scrape missing companies from Glassdoor (rate-limited, max 20/run)
  4. Store in company_reviews table
  5. Feed into ghost/genuineness scoring
```

### Ghost model enhancement with Glassdoor data

```
Updated ghost scoring with company intelligence:

  ghost_score inputs:
    ... existing signals ...
    + company_has_reviews    × 0.10  — no presence = slightly suspicious
    + company_rating         × 0.05  — very low rating = might be churning employees
    + interview_process_exists × 0.10 — has interview data = real hiring process

  acceptance_probability inputs:
    + interview_difficulty   — calibrate preparation needed
    + salary_data            — is the role worth pursuing financially?
    + company_size           — startup vs enterprise (different hiring bar)
```

### Budget estimate

- ~20 companies per run × ~200KB per page = ~4MB per run
- Well within DataImpulse 5GB/month budget
- Cache aggressively: company reviews don't change daily, rescrape monthly

---

## End of Day Checkpoint

By end of tomorrow you should have:
- `intelligence.db` with 642 jobs backfilled, auto-recording on every scrape
- Ghost detection working and validated against known suspects
- Blocker filter catching visa/language/clearance disqualifiers
- `analyze` command in pipeline producing actionable tiers
- Longer descriptions flowing from scrapers (3000 chars)
- Glassdoor scraper pulling company reviews for top companies
- Company intelligence feeding into ghost scores

**What this unlocks for the day after:**
- Run a fresh scrape + full pipeline with intelligence → first real "apply to these" list
- Ghost scores improve automatically with each run (more data = better patterns)
- Company reviews cached — repeat runs skip already-scraped companies
- Ready to add acceptance probability scoring (Phase 9)

---

## Files touched

| File | Change | Grade |
|------|--------|-------|
| `ranker/intelligence_db.py` | NEW — SQLite DB manager | G4 |
| `ranker/ghost_detector.py` | NEW — ghost scoring model | G3 |
| `scripts/pipeline.py` | Add record_to_db hook + cmd_analyze | G3 |
| `scraper/base.py` or individual scrapers | Raise description cap | G2 |
| `scraper/glassdoor.py` | NEW — company review scraper | G3 |
| `plan/offer_intelligence.md` | Update with what was built | G1 |
