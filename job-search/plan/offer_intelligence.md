# Offer Intelligence — Prediction Model Plan

## Goal

Build a **prediction engine** that accumulates knowledge across runs and scores each offer on:

1. **Is it real?** (genuineness — vs ghost job, market study, internal-hire)
2. **Can I get it?** (acceptance probability — given my profile, blockers, competition)
3. **Should I invest time?** (opportunity score — combining both)

---

## Current State

- **5 runs** stored, **509 unique jobs** (title+company), **99 already seen in 2+ runs**
- We have: title, company, location, url, source, date_posted, description (500 chars), composite score breakdown
- We don't have: full descriptions for most sources, company metadata, posting history beyond 5 runs
- Date format inconsistent: epoch (arbeitnow) vs ISO string (remoteok, linkedin)

---

## The Prediction Model

### Architecture: 3 Layers

```
Layer 1: OBSERVATION (per-run, per-job)
  Raw signal extraction from job data
  Output: signal vector per job

Layer 2: MEMORY (cross-run, persistent)
  Accumulate observations, detect patterns over time
  Output: enriched signals (repost count, company profile, market patterns)

Layer 3: PREDICTION (per-job verdict)
  Combine Layer 1 + Layer 2 into scores and verdicts
  Output: genuineness, acceptance probability, blockers, opportunity score
```

### Layer 1 — Observation Engine (per job, per run)

Extracts raw signals from each job. No history needed — works on day 1.

#### 1a. Posting Freshness

```
Input:  date_posted (epoch or ISO)
Output: age_days (int), freshness_tier (fresh/normal/stale/ancient)

Rules:
  fresh:   0–7 days    → likely real, active hiring
  normal:  8–30 days   → standard pipeline
  stale:   31–60 days  → might be ghost, slow process, or niche role
  ancient: 60+ days    → almost certainly ghost or market study
```

#### 1b. Description Analysis

```
Input:  description text
Output: specificity_score (0–1), extracted signals dict

Signals to extract:
  - team_mention:      "team of N", "join our X team"      → real
  - project_mention:   "building X", "migrating to Y"      → real
  - tech_versions:     "Kubernetes 1.28", "Terraform 1.5"   → real (specific)
  - generic_buzzwords: "fast-paced", "synergy", "rockstar"  → ghost signal
  - salary_mentioned:  any salary range or "competitive"     → real signal
  - process_mentioned: "interview stages", "take-home"       → real signal
  - urgency_signal:    "immediate", "backfill", "ASAP"       → real signal
  - benefits_detail:   specific perks, not just "competitive" → real signal
  - requirement_count: number of distinct skills/certs asked  → overloaded = study

Specificity formula:
  specific_count = team + project + tech_versions + salary + process + urgency
  generic_count  = buzzword_density + vague_requirements
  specificity    = specific_count / (specific_count + generic_count + 1)
```

#### 1c. Employer Classification

```
Input:  company name
Output: employer_type (direct | agency | consultancy | unknown)

Detection:
  - Agency patterns:    "staffing", "recruiting", "talent", "hays", "adecco",
                        "randstad", "manpower", "robert half", "michael page"
  - Consultancy patterns: "consulting", "solutions", "services", "partners"
  - Direct:             everything else (with confidence based on name structure)

Why it matters:
  - Agency posts are often market studies or have multiple clients
  - Same agency posting same role repeatedly = building candidate pool
  - Direct employer + specific description = highest genuineness
```

#### 1d. Blocker Extraction (candidate-specific)

```
Input:  description + location + title
Output: list of {type, severity, detail}

Blocker types:
  VISA:        "authorized to work", "no sponsorship", "EU/US citizens only"
  LANGUAGE:    "fluent German required", "native French", "German C1/C2"
  LOCATION:    "on-site only", "must reside in", "no remote"
  EXPERIENCE:  "10+ years", "15 years minimum" (vs candidate's 5)
  CLEARANCE:   "security clearance", "government", "classified"
  CERTIFICATION: "CKA required", "must hold AWS SA Pro" (vs "preferred")

Severity classification:
  HARD:      "required", "must have", "mandatory"     → disqualifying
  SOFT:      "preferred", "nice to have", "ideally"   → not a blocker
  UNCERTAIN: mentioned without qualifier               → needs investigation
```

#### 1e. Seniority Alignment

```
Input:  title + description
Output: seniority_gap (int), alignment_tier

Extract required years:  regex for "N+ years", "N-M years experience"
Extract seniority level: "junior/mid/senior/staff/principal/lead/director"

Alignment:
  match:       title=Senior + asks 3-7 years         → good fit
  stretch:     title=Senior + asks 7-10 years         → possible, highlight gap
  overqualified: title=Junior + candidate is senior   → waste of time
  underqualified: asks 10+ years or Staff/Principal   → low probability
```

---

### Layer 2 — Memory Engine (cross-run, persistent)

Stores in `output/offer_history.json`. Grows with each run.

#### 2a. Offer Fingerprinting & Tracking

```
Database: output/offer_history.json

Schema per entry:
{
  "fingerprint": "devops-engineer::memx",       // lowercase(title)::lowercase(company)
  "urls": ["https://..."],                       // all URLs seen (may change across sources)
  "sources": ["remoteok", "arbeitnow"],          // posted on multiple sites = wider search
  "first_seen": "2026-03-06",                    // earliest run
  "last_seen": "2026-03-08",                     // most recent run
  "seen_count": 3,                               // number of runs it appeared in
  "seen_in_runs": ["2026-03-06-...", "2026-03-07-...", "2026-03-08-..."],
  "status_history": [                            // track if it disappears and reappears
    {"date": "2026-03-06", "status": "seen"},
    {"date": "2026-03-07", "status": "seen"},
    {"date": "2026-03-08", "status": "not_seen"},  // gap
    {"date": "2026-03-09", "status": "seen"},       // repost!
  ]
}
```

#### 2b. Pattern Detection from History

```
From accumulated data, derive:

REPOST DETECTION:
  seen_count > 3 across 30+ days           → ghost job (always open)
  disappeared then reappeared               → repost (reset applicant pool)
  same company, 3+ similar titles           → mass hiring OR market study

COMPANY BEHAVIOR PROFILING:
  company posts N jobs across M runs:
    high N, all similar roles               → staffing agency behavior
    high N, diverse roles                   → real growth (good signal)
    same role, different URLs               → reposting (bad signal)
    posts then removes within 14 days       → real hiring (filled fast)

MARKET SIGNALS:
  same title from 5+ companies             → hot market for that role
  title appears then disappears quickly     → real demand (gets filled)
  title persists across many runs           → either niche or ghost
```

#### 2c. Company Intelligence Cache

```
Database: output/company_intel.json

Schema per company:
{
  "company": "MEMX",
  "total_postings_seen": 5,
  "unique_roles_seen": 3,
  "avg_posting_lifespan_days": 18,
  "sources_used": ["remoteok", "linkedin"],
  "is_agency": false,
  "hiring_velocity": "moderate",          // derived: roles/month
  "ghost_risk": "low",                    // derived: avg lifespan < 30d
  "first_seen": "2026-03-06",
  "last_seen": "2026-03-08"
}
```

---

### Layer 3 — Prediction Engine (per-job verdict)

Combines Layer 1 signals + Layer 2 history into final scores.

#### 3a. Genuineness Score (0.0 – 1.0)

```
Inputs (weighted):
  freshness_tier    × 0.20   (fresh=1.0, normal=0.7, stale=0.3, ancient=0.1)
  specificity_score × 0.25   (from description analysis)
  employer_type     × 0.15   (direct=1.0, consultancy=0.6, agency=0.3)
  repost_signal     × 0.20   (never_reposted=1.0, once=0.6, chronic=0.1)
  company_ghost_risk× 0.10   (from company intel cache)
  multi_source      × 0.10   (posted on 1 site=0.5, 2+=0.8 — wider reach = real need)

Verdict mapping:
  0.70+ → LIKELY_REAL
  0.45–0.70 → UNCERTAIN
  below 0.45 → LIKELY_GHOST_OR_STUDY
```

#### 3b. Acceptance Probability (0.0 – 1.0)

```
Start at 1.0, apply penalties:

  hard_blocker_count > 0:  × 0.05 per blocker    (nearly disqualifying)
  soft_blocker_count:      × 0.85 per blocker     (minor penalty)
  seniority_gap > 3 years: × 0.60                 (stretch)
  seniority_gap > 5 years: × 0.30                 (unlikely)
  is_agency:               × 0.90                 (agencies = wider funnel)
  skill_match < 0.3:       × 0.70                 (weak skill overlap)
  location mismatch:       × 0.80                 (relocation friction)
  visa_uncertain:          × 0.70                 (unknown sponsorship)

Final = base × all penalties, clamped to [0.0, 1.0]
```

#### 3c. Overall Opportunity Score

```
opportunity = genuineness × 0.40 + acceptance × 0.35 + composite_score × 0.25

This balances:
  - Is the job real?           (don't waste time on ghosts)
  - Can I actually get it?     (don't waste time on impossible ones)
  - Does it match my skills?   (don't waste time on poor fits)
```

#### 3d. Verdict & Reasoning

```
Categories:
  STRONG_OPPORTUNITY  — genuine + high acceptance + good fit
  WORTH_APPLYING      — genuine + moderate acceptance, some challenges
  LONG_SHOT           — genuine but significant blockers
  LIKELY_GHOST        — low genuineness regardless of fit
  MARKET_STUDY        — agency + chronic repost + generic description
  BLOCKED             — hard blockers make it impossible

Each verdict includes:
  - 1-line reason: "Fresh posting, direct employer, but requires German C1"
  - challenges[]: specific obstacles for this candidate
  - advantages[]: what works in candidate's favor
```

---

## Output Schema (per job)

```json
{
  "offer_intelligence": {
    "genuineness": 0.72,
    "acceptance": 0.45,
    "opportunity": 0.58,
    "verdict": "WORTH_APPLYING",
    "verdict_reason": "Real posting (12d old, specific stack), but German C1 is a soft blocker",

    "signals": {
      "age_days": 12,
      "freshness": "fresh",
      "specificity": 0.65,
      "employer_type": "direct",
      "repost_count": 0,
      "first_seen": "2026-03-07",
      "multi_source": false
    },

    "blockers": [
      {"type": "language", "severity": "soft", "detail": "German preferred (not required)"}
    ],

    "challenges": ["German language preferred", "On-site Munich — relocation needed"],
    "advantages": ["Strong Kubernetes match", "5yr experience fits Senior title", "Azure stack aligned"]
  }
}
```

---

## Implementation Sequence

```
Step 1: offer_history.json — Start recording every job across runs NOW
        (the sooner we start, the more data Layer 2 has)
        File: ranker/offer_history.py
        Trigger: runs automatically at end of scrape stage

Step 2: Layer 1 signals — Observation engine
        File: ranker/offer_intelligence.py
        Functions: extract_signals(job) → signal dict
        No dependencies, works on day 1

Step 3: Layer 2 queries — Read from history for repost/company patterns
        File: ranker/offer_history.py (add query functions)
        Functions: get_repost_count(), get_company_profile(), detect_ghost()

Step 4: Layer 3 prediction — Combine into scores + verdict
        File: ranker/offer_intelligence.py (add predict())
        Functions: predict(job, history_signals) → offer_intelligence dict

Step 5: Pipeline integration — New "analyze" stage
        File: scripts/pipeline.py (add cmd_analyze)
        Position: after validate, before prepare
        Output: analyzed.json
```

### Dependency Direction

```
pipeline.py --> offer_intelligence.py (analyze stage)
pipeline.py --> offer_history.py (record after scrape, query during analyze)
offer_intelligence.py --> offer_history.py (Layer 2 queries)
offer_intelligence.py --> ranker/config.py (candidate profile, skills)
offer_history.py --> output/offer_history.json (persistent)
offer_history.py --> output/company_intel.json (persistent, derived)
prepare/rank stages can consume offer_intelligence fields downstream
```

---

## Critical Dependency: Description Length

Current descriptions are truncated to ~500 chars. Layer 1 signal extraction (specificity, blockers, seniority) degrades significantly with short text.

**Action needed:**
- Increase description capture in scrapers (at least 2000 chars)
- Run enrichment stage for Indeed (already exists)
- Consider enrichment for other sources (fetch full job page)

**Without longer descriptions:** genuineness scoring still works (age, company, repost patterns), but blocker detection and specificity scoring will be unreliable.

---

## What We Start Collecting NOW

Even before building the prediction engine, **Step 1 (offer_history.json) should run immediately**. Every run that passes without recording is lost data. The more history we accumulate, the better ghost detection and company profiling become.

Minimum viable recording per scrape run:
```python
for job in scraped_jobs:
    fingerprint = f"{job['title'].lower().strip()}::{job['company'].lower().strip()}"
    record(fingerprint, job['url'], job['source'], run_timestamp)
```
