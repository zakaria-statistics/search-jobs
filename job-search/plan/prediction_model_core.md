# Prediction Model — What's Actually Inside

## What It Is

A **rule-based scoring system with statistical feedback**, not a machine learning model.

## What It Is NOT

- Not a neural network
- Not a trained ML model (no training data yet)
- Not GPT/Claude doing classification (too expensive per job)
- Not a recommendation engine

## What Is a Signal?

A **signal** is a single measurable fact about a job, normalized to a 0.0–1.0 scale, that hints whether the job is real or ghost.

```
Signal = raw data point → simple function → normalized float (0.0–1.0)

Examples:

  "This job was posted 45 days ago"
      raw data:   date_posted = 2026-01-22
      function:   age_signal(date_posted) → maps age brackets to float
      output:     0.6  (stale, leaning ghost)

  "This company name contains 'Staffing'"
      raw data:   company = "MY Humancapital GmbH"
      function:   employer_signal(company) → regex match against agency patterns
      output:     0.8  (looks like agency)

  "This job appeared in 8 out of 5 scrape runs"
      raw data:   seen_count = 8
      function:   repost_signal(seen_count, observation_days) → frequency ratio
      output:     0.95 (chronic reposter)

  "Description is 500+ chars with specific tech versions"
      raw data:   description = "Kubernetes 1.28, Terraform modules..."
      function:   description_signal(text) → count specific vs generic terms
      output:     0.1  (specific = likely real)

  "Company has 4.2 stars on Glassdoor with 200 reviews"
      raw data:   glassdoor rating = 4.2, review_count = 200
      function:   company_signal(rating, reviews) → weighted presence check
      output:     0.1  (established company, likely real)
```

Each signal answers exactly one question:

```
  CORE SIGNALS (Phase 1):
  Signal                Question it answers
  ────────────────────  ──────────────────────────────────────────
  age_signal            How old is this posting?
  repost_signal         Does it keep reappearing across runs?
  employer_signal       Is this a staffing agency or direct employer?
  description_signal    Is the description specific or generic?
  company_signal        Does external data confirm this company is legit?

  RESEARCH-BACKED SIGNALS (Phase 1b):
  Signal                Question it answers
  ────────────────────  ──────────────────────────────────────────
  pipeline_signal       Does it use "talent community"/"always looking" language?
  careers_page_signal   Is this job on the company's own careers website?
  desc_hash_signal      Did they refresh the date but keep identical text?
  contact_signal        Is there a named recruiter or hiring manager?
```

### Research Backing (2025–2026 data)

```
  Industry statistics:
    18–27% of all job listings are ghosts (Greenhouse, ResumeUp.AI)
    1 in 3 employers admit posting with no intent to hire (Clarify Capital)
    45% of HR professionals "regularly" post ghost jobs
    Real jobs fill in 30–45 days; 60+ days = red flag

  Why companies post ghosts:
    62% — make current employees feel replaceable
    43% — appear to be growing (investor optics)
    38% — maintain job board presence
    36% — test job descriptions / gauge salary expectations

  Confirmed detection patterns mapped to our signals:
    posting age 30+ days               → age_signal       ✓
    cyclical reposting                 → repost_signal    ✓
    vague "competitive pay" language   → description_signal ✓
    staffing agency repeated posting   → employer_signal   ✓
    not on company careers page        → careers_page_signal (new)
    "always looking" / "talent pool"   → pipeline_signal    (new)
    date refreshed, same description   → desc_hash_signal   (new)
    no recruiter name / contact        → contact_signal     (new)

  Sources:
    - Greenhouse 2025 study (18–22% ghost rate)
    - ResumeUp.AI LinkedIn analysis (27.4% ghost rate)
    - Clarify Capital Jan 2025 (1 in 3 employers admit ghost posting)
    - MintCareer Ghost Jobs Guide 2026
    - Code Pulse Feb 2026 (3/47 = 6.4% real application rate)
```

Signals are **independent** — each one works alone. The scorer combines them:

```
  UPDATED GHOST SCORE (9 signals):

  ghost_score = age        × 0.15      ← old posting = ghost
              + repost     × 0.15      ← chronic reposter = ghost
              + employer   × 0.15      ← agency = ghost risk
              + desc       × 0.10      ← vague description = ghost
              + company    × 0.10      ← no external presence = suspicious
              + pipeline   × 0.10      ← "talent pool" language = ghost
              + careers    × 0.10      ← not on careers page = ghost
              + desc_hash  × 0.10      ← refreshed date, same text = ghost
              + contact    × 0.05      ← no named recruiter = minor signal
              ─────────────────
              = 0.0 (definitely real) to 1.0 (definitely ghost)
```

**Why 0–1 normalization matters:** All signals speak the same language. Without it, "seen_count = 8" and "age_days = 45" have different scales and can't be combined. Normalization makes them comparable.

---

## The Core: Weighted Scoring + Bayesian Updates

### Phase 1 (tomorrow): Heuristic Scorer

```
Type:       Weighted linear combination
Math:       score = Σ(signalᵢ × weightᵢ)
Complexity: ~50 lines of Python, no dependencies

It's the same math as composite_score.py (which already works).
Just different signals and different weights.
```

**How it works:**

```python
def ghost_score(job, history):
    age     = age_signal(job["date_posted"])        # 0.0–1.0
    repost  = repost_signal(history["seen_count"])   # 0.0–1.0
    agency  = employer_signal(job["company"])         # 0.0–1.0
    desc    = description_signal(job["description"]) # 0.0–1.0
    company = company_signal(history["reviews"])      # 0.0–1.0

    return (age     * 0.25 +
            repost  * 0.25 +
            agency  * 0.20 +
            desc    * 0.15 +
            company * 0.15)
```

That's it. Each signal is a simple function that maps raw data to a 0–1 float.
Weights are hand-tuned based on domain knowledge. No training needed.

### Phase 2 (after ~50 applications): Bayesian Weight Tuning

```
Type:       Bayesian probability updates
Math:       P(ghost | signals) = P(signals | ghost) × P(ghost) / P(signals)
Trigger:    When we have outcome data (applied → response or ghosted)

What changes:
  - Weights stop being hand-tuned
  - Each outcome updates our belief about which signals matter
  - "repost_frequency predicted ghost correctly 90% of the time" → increase its weight
  - "employer_type was wrong 40% of the time" → decrease its weight
```

**Concrete example:**

```
Prior (hand-tuned):      repost_weight = 0.25
After 30 outcomes:       repost correctly predicted 27/30 ghosted jobs
Updated:                 repost_weight → 0.32 (model learned it's more important)

Prior:                   employer_weight = 0.20
After 30 outcomes:       employer type was wrong for 12/30 jobs
Updated:                 employer_weight → 0.14 (model learned it's less reliable)
```

### Phase 3 (after ~200 applications): Statistical Model

```
Type:       Logistic regression (sklearn, ~10 lines)
Math:       P(real) = 1 / (1 + e^(-(β₀ + β₁x₁ + β₂x₂ + ...)))
Trigger:    When we have enough labeled data to train properly

What changes:
  - Replace hand-tuned weights with learned coefficients
  - Model discovers non-obvious patterns:
    "jobs posted on Tuesday from direct employers have 3x response rate"
  - Still interpretable (logistic regression shows which features matter)
```

## Why Not ML From Day 1?

```
ML needs:    labeled training data (hundreds of ghost/real examples)
We have:     0 labeled examples right now
Solution:    start with rules, collect labels through outcomes, graduate to ML

Timeline:
  Day 1–30:    heuristic scorer (rules + weights)     ← tomorrow
  Day 30–90:   bayesian updates (weights self-adjust)  ← after ~50 applications
  Day 90+:     logistic regression (if needed)          ← after ~200 applications
  Maybe never: deep learning (overkill for this problem)
```

## Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│              INTELLIGENCE SYSTEM                    │
│                                                     │
│  ┌──────────────┐   ┌────────────────┐              │
│  │ DATA LAYER   │   │ KNOWLEDGE LAYER│              │
│  │              │   │                │              │
│  │ SQLite DB    │   │ Signal funcs   │              │
│  │ • offers     │   │ • age_signal() │              │
│  │ • sightings  │   │ • repost()     │              │
│  │ • companies  │   │ • employer()   │              │
│  │ • outcomes   │   │ • desc_qual()  │              │
│  │              │   │ • company()    │              │
│  └──────┬───────┘   └───────┬────────┘              │
│         │                   │                       │
│         ▼                   ▼                       │
│  ┌──────────────────────────────────┐               │
│  │         SCORING ENGINE           │               │
│  │                                  │               │
│  │  Phase 1: Σ(signal × weight)     │  ← tomorrow  │
│  │  Phase 2: Bayesian weight update │  ← month 2   │
│  │  Phase 3: Logistic regression    │  ← month 3+  │
│  │                                  │               │
│  └──────────────┬───────────────────┘               │
│                 │                                   │
│                 ▼                                   │
│  ┌──────────────────────────────────┐               │
│  │       DECISION ENGINE            │               │
│  │                                  │               │
│  │  ghost_score → REAL / GHOST      │               │
│  │  blockers    → BLOCKED / CLEAR   │               │
│  │  opportunity → APPLY / SKIP      │               │
│  │                                  │               │
│  └──────────────┬───────────────────┘               │
│                 │                                   │
│                 ▼                                   │
│  ┌──────────────────────────────────┐               │
│  │       FEEDBACK LOOP              │               │
│  │                                  │               │
│  │  outcome (response/ghosted)      │               │
│  │  → update signal weights         │  ← month 2+  │
│  │  → retrain model                 │  ← month 3+  │
│  │                                  │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

## Time-Risk Model — Is This Job Worth My Hours?

### The Problem

```
Not all applications cost the same:

  Job A: 30 min apply → ghosted               = 0.5 hrs wasted
  Job B: 3 hrs apply → interview → rejected    = 10 hrs wasted
  Job C: 3 hrs apply → interview → HIRED       = 10 hrs invested (worth it)
  Job D: 2 days prep → 4 rounds → visa reject  = 20 hrs wasted on impossible job

The goal: maximize P(hired) per hour invested.
```

### Two Dimensions: Effort vs Risk

```
EFFORT ESTIMATE (how much time this application will cost):

  Signal                    Indicator                          Effort level
  ────────────────────────  ─────────────────────────────────  ────────────
  Application method        "Easy apply" / "Quick apply"       LOW (30 min)
  Application method        "Apply on company site"            MEDIUM (1-2 hrs)
  Application method        "Send CV + cover letter to email"  MEDIUM (2-3 hrs)
  Take-home mentioned       "coding challenge", "case study"   HIGH (4-8 hrs)
  Multi-round process       "4-stage interview"                HIGH (8-20 hrs total)
  Portfolio required        "send examples of your work"       HIGH (4-8 hrs)
  Cover letter required     explicitly asks for cover letter   MEDIUM (+1-2 hrs)

  effort_hours = base_apply + cover_letter + take_home + interview_rounds


REJECTION RISK (probability of getting rejected AND at which stage):

  Risk type                  When you find out         Hours already spent
  ─────────────────────────  ────────────────────────  ────────────────────
  ATS auto-reject            Immediately (0-1 day)     0.5 hrs (minimal loss)
  Recruiter screen reject    After 1 week              1-2 hrs
  Visa/location reject       After 1-3 rounds          10-20 hrs (PAINFUL)
  Seniority reject           After technical round      10-15 hrs
  Culture fit reject         Final round                15-20 hrs
  Offer too low              After full process         15-20 hrs
  Ghosted (no response)      Never (you wait 30 days)   0.5-3 hrs

  LATE REJECTION = worst outcome (high effort already spent)
  EARLY REJECTION = acceptable (low effort wasted)
```

### Time-Risk Score

```
Formula:
  time_risk = effort_hours × P(late_rejection)

  Where P(late_rejection) = probability of being rejected AFTER investing
  significant time (post-recruiter-screen stage)

  Late rejection predictors:
    visa_uncertain     → 0.60  (most common late-stage killer)
    seniority_gap > 3  → 0.40  (passes screen, fails technical)
    language_soft      → 0.30  (might pass screen, fail interview)
    salary_mismatch    → 0.25  (survives until offer stage)
    location_reloc     → 0.20  (discussed late in process)

  P(late_rejection) = 1 - Π(1 - risk_factor) for each applicable risk

  time_risk interpretation:
    < 1.0 hrs  → LOW RISK     (fast apply, unlikely late rejection)
    1-5 hrs    → MODERATE     (some effort, some risk)
    5-10 hrs   → HIGH         (significant time could be wasted)
    > 10 hrs   → DANGEROUS    (multi-day investment with real rejection chance)
```

### Combined Opportunity Matrix

```
                        Low Effort              High Effort
                    ┌─────────────────────┬─────────────────────┐
                    │                     │                     │
  Low Risk          │   QUICK WIN         │   WORTH INVESTING   │
  (no blockers,     │   Apply immediately │   Prepare well,     │
   high match)      │   even if fit is    │   high payoff       │
                    │   moderate          │                     │
                    ├─────────────────────┼─────────────────────┤
                    │                     │                     │
  High Risk         │   LOTTERY TICKET    │   TIME TRAP         │
  (has soft         │   Quick apply,      │   ⚠ WARNING ⚠       │
   blockers)        │   don't invest      │   High effort +     │
                    │   heavily           │   likely rejected   │
                    │                     │   late. SKIP unless │
                    │                     │   dream job.        │
                    └─────────────────────┴─────────────────────┘

  Labels (added to each job's verdict):

  QUICK WIN       — effort < 2hrs, time_risk < 1.0
                    "Apply today, 30 min, good odds"

  WORTH INVESTING — effort > 2hrs, time_risk < 3.0
                    "Takes prep, but low rejection risk"

  LOTTERY TICKET  — effort < 2hrs, time_risk 1.0-5.0
                    "Quick apply, might get lucky, don't over-invest"

  TIME TRAP       — effort > 2hrs, time_risk > 5.0
                    "⚠ You'll spend days and likely get rejected at round 3"
```

### Effort Detection from Description (regex)

```python
EFFORT_SIGNALS = {
    "easy_apply":     (r"easy apply|quick apply|one.click", -2),  # reduces effort
    "cover_letter":   (r"cover letter|lettre de motivation", +2),  # adds hours
    "take_home":      (r"take.home|coding challenge|case study|technical test", +6),
    "portfolio":      (r"portfolio|work samples|examples of", +4),
    "multi_round":    (r"(\d+).*(round|stage|step).*interview", +3),  # per round
    "video_intro":    (r"video introduction|video pitch", +2),
    "references":     (r"references required|provide references", +1),
}

base_effort = 1.0  # hours (minimum: find job, read, decide, submit)
for signal, (pattern, hours) in EFFORT_SIGNALS.items():
    if re.search(pattern, description, re.I):
        base_effort += hours
```

### Integration with Existing Tiers

```
BEFORE (ghost + blocker + fit):
  APPLY NOW / WORTH EFFORT / LONG SHOT / SKIP

AFTER (+ time-risk):
  APPLY NOW
    ├── QUICK WIN        (low effort, do it now)
    └── WORTH INVESTING  (high effort, but high payoff)
  WORTH EFFORT
    ├── LOTTERY TICKET   (quick apply, don't over-invest)
    └── ⚠ TIME TRAP      (careful — could waste days)
  LONG SHOT
    └── LOTTERY TICKET   (only if quick apply available)
  SKIP
    └── SKIP             (ghost / blocked / no match)

Terminal output:
  ═══════════════════════════════════════════════════════════════
    QUICK WINS (apply today, <1hr each):
      1. DevOps Engineer @ MEMX        opp=0.87  effort=0.5hr  risk=LOW
      2. Cloud Engineer @ Kunai        opp=0.72  effort=1hr    risk=LOW

    WORTH INVESTING (prepare this week):
      3. Platform Eng @ CEF AI         opp=0.68  effort=4hrs   risk=LOW
         → has take-home test, but no blockers

    LOTTERY TICKETS (quick apply, don't over-invest):
      4. SRE @ BigCorp                 opp=0.45  effort=0.5hr  risk=MOD
         → visa uncertain, but easy apply

    ⚠ TIME TRAPS (skip unless dream job):
      5. DevOps @ MunichCorp           opp=0.52  effort=8hrs   risk=HIGH
         → 4-round process + German C1 soft blocker
         → likely rejected at interview stage for language
  ═══════════════════════════════════════════════════════════════
```

---

## In One Sentence

Start with **weighted rules** (like composite_score.py already does), collect outcome data through the application tracker, then **let the data teach the model which signals actually predict ghost jobs** — graduating from hand-tuned weights → Bayesian updates → logistic regression as data accumulates.
