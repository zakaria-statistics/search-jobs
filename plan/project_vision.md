# Project Vision — Future Snapshot

What the project looks like when fully realized. Read top-to-bottom: done phases first, then planned phases building on accumulated data and infrastructure.

---

## Completed Phases

### Phase 1: Foundation — Basic Scraping ✓
Collect raw job data from multiple sources into structured JSON.

### Phase 2: AI Ranking — Claude Integration ✓
Score jobs against candidate profile using LLM.

### Phase 3: Semantic Intelligence — Vector DB + RAG ✓
Match jobs to resume variants using embeddings, feed context to Claude.

### Phase 4: Composite Scoring — Multi-Signal Ranking ✓
Replace single-signal sorting with weighted multi-dimension scoring.

### Phase 5: Pipeline Maturity — Tracking & Workflow ✓
End-to-end pipeline with run dirs, trackers, interactive review.

---

## Planned Phases

### Phase 6: Feedback Loop — Score Calibration
**Goal:** Learn from outcomes to improve scoring accuracy over time.

**Why now:** We have `opportunities.json` tracking application outcomes (applied, interview, rejected, accepted) and `filtered_*.json` with composite scores. The link between "what we scored high" and "what actually led to interviews" is the missing signal.

```
opportunities.json (outcomes) + runs/*/filtered_*.json (scores)
    ↓ correlate
outcome_feedback.json — which score ranges led to interviews vs rejections
    ↓ feed back
ranker/config.py — auto-adjust COMPOSITE_WEIGHTS based on outcome data
```

| Feature | Detail |
|---------|--------|
| Outcome linking | Match tracked opportunities back to their original scores |
| Score-to-outcome correlation | "Jobs scored 0.80+ led to interviews 40% of the time vs 5% for 0.50-0.60" |
| Weight suggestion | "Increasing title_match weight from 0.20 to 0.25 would have ranked 3 more interview-jobs in top bucket" |
| Confidence tracking | How many data points back each weight — don't adjust on small samples |
| **Data:** | `output/feedback.json` — persistent, grows with each outcome update |

**Depends on:** Phase 4 (composite scores), Phase 5 (opportunity tracker with outcomes)

---

### Phase 7: Market Intelligence — Trend Analytics
**Goal:** Aggregate data across runs to reveal market patterns over time.

**Why now:** Every pipeline run produces `filtered_*.json` with skill breakdowns, scores, locations, and sources. Across weeks of runs, this becomes a dataset showing what the market demands.

```
output/runs/*/filtered_*.json (accumulated across weeks)
    ↓ aggregate
output/trends.json — skill frequency, salary signals, demand by region
    ↓ visualize
plan/market_dashboard.html — charts over time
```

| Feature | Detail |
|---------|--------|
| Skill demand tracking | Which skills appear most across top-bucket jobs, trending up or down |
| Regional heat map | Where demand concentrates — Paris vs remote vs Germany |
| Source quality | Which scraper sources produce the most interview-worthy jobs |
| Company frequency | Companies that post repeatedly — likely active hiring vs stale listings |
| Salary signal extraction | Parse salary mentions from descriptions, track ranges by role/region |
| **Data:** | `output/trends.json` — append-only, one entry per run |

**Depends on:** Phase 1 (scraped data), Phase 4 (score breakdowns), accumulated runs over time

---

### Phase 8: Auto-Application — Resume Tailoring + Cover Letters
**Goal:** Generate application materials tailored to each specific job.

**Why now:** We have matched resume chunks (RAG context) per job, composite score breakdowns showing which skills match, and Claude API already integrated. The inputs for personalization exist.

```
filtered_top.json (job + score_breakdown + relevant_chunks)
    ↓ Claude API
output/runs/{ts}/applications/
    ├── company_role_cover_letter.md
    └── company_role_resume_tweaks.md
```

| Feature | Detail |
|---------|--------|
| Cover letter generation | 3-4 sentence cover note per job, using matched skills + score breakdown |
| Resume tweak suggestions | Already exists in ranked output — promote to standalone actionable doc |
| Stack-specific emphasis | Use `matched_stack` to pick which resume variant to customize |
| Batch generation | Generate for all top-bucket jobs in one run |
| Template system | User-editable templates in `docs/`, Claude fills in the blanks |
| **Data:** | Per-run under `output/runs/{ts}/applications/` |

**Depends on:** Phase 3 (RAG context), Phase 4 (score breakdown with matched/missing skills)

---

### Phase 9: Interview Prep — Company-Specific Preparation
**Goal:** Auto-generate interview preparation materials when a job moves to "Interview" status.

**Why now:** Opportunity tracker has status flow. When status changes to "Interview", we know the company, role, matched skills, and missing skills. Enough context for targeted prep.

```
opportunities.json (status: Interview) + original job data + relevant_chunks
    ↓ Claude API
output/interview_prep/
    └── company_role_prep.md
```

| Feature | Detail |
|---------|--------|
| Company research summary | What the company does, tech stack signals from job description |
| STAR stories mapping | Match candidate experience to likely interview questions |
| Technical focus areas | Based on missing_skills — what to brush up on |
| Culture signals | Extract from description tone, benefits, team structure mentions |
| Question bank | Role-specific questions to ask the interviewer |
| **Data:** | `output/interview_prep/` — persistent, one file per interview |

**Depends on:** Phase 5 (opportunity tracker status flow), Phase 2 (Claude integration)

---

### Phase 10: Notifications — Passive Monitoring
**Goal:** Run scraping on a schedule and get notified when high-score jobs appear, instead of manually running the pipeline.

```
cron / systemd timer → pipeline.py scrape + filter
    ↓ if top bucket has new jobs
notification (email / Slack / desktop)
    ↓ user reviews when convenient
pipeline.py review
```

| Feature | Detail |
|---------|--------|
| Scheduled scraping | cron job or systemd timer, configurable frequency |
| New-job detection | Compare against previous run to identify genuinely new listings |
| Threshold alerting | Notify only when composite score exceeds user-defined threshold |
| Dedup across runs | Don't alert for jobs already seen in previous runs |
| Channel options | Email, Slack webhook, desktop notification, or just a log file |
| **Data:** | `output/seen_jobs.json` — persistent set of already-notified job URLs |

**Depends on:** Phase 1 (scraping), Phase 4 (composite scoring), Phase 5 (run dirs)

---

## Dependency Map — All Phases

```
Phase 1: Scraping ──────────────────────────────────────┐
    ↓                                                    │
Phase 2: AI Ranking ─────────────────────────┐          │
    ↓                                         │          │
Phase 3: Semantic + RAG ─────────┐           │          │
    ↓                             │           │          │
Phase 4: Composite Scoring ──────┤           │          │
    ↓                             │           │          │
Phase 5: Pipeline Maturity       │           │          │
    ↓                             ↓           ↓          ↓
Phase 6: Feedback Loop        Phase 8     Phase 9    Phase 10
    ↓                         Auto-App    Interview  Notifications
Phase 7: Market Intelligence  (3,4)       Prep (2,5) (1,4,5)
    (1,4,runs)
```

**Read order:**
- **Sequential (must build in order):** 1 → 2 → 3 → 4 → 5
- **Parallel (independent after Phase 5):** 6, 7, 8, 9, 10 can be built in any order
- **Highest value next:** Phase 6 (feedback loop) — it improves everything downstream by calibrating scores

---

## Single-Run Data Flow — Complete Picture

```
scrape → scraped.json
    ↓
enrich → scraped.json (enriched Indeed descriptions)
    ↓
filter → filtered_top.json + filtered_strong.json + filtered_moderate.json
    ↓
rank → ranked.json
    ↓
review → opportunities.json (approved jobs)
    ↓                              ↓
[Phase 8] applications/        [Phase 9] interview_prep/
    cover letters                  company prep docs
                                       ↓
                              [Phase 6] feedback.json
                                  outcome → weight calibration
```

## Cross-Run Data Flow — Accumulated Intelligence

```
run 1: filtered_top.json ──┐
run 2: filtered_top.json ──┤
run 3: filtered_top.json ──┼──→ [Phase 7] trends.json → market dashboard
run N: filtered_top.json ──┘
                               [Phase 10] seen_jobs.json → dedup + alerts
                               [Phase 6]  feedback.json  → weight tuning
```
