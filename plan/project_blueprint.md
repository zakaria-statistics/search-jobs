# Project Blueprint — Generic Build Pattern

How to think about building any data-driven automation project from zero to complete.

---

## The 4 Layers

Every project that collects, processes, and acts on data follows this stack:

```
Layer 4: ACTION        → do something with the intelligence (apply, alert, generate)
Layer 3: INTELLIGENCE  → score, rank, predict, recommend
Layer 2: ENRICHMENT    → clean, enrich, link, embed
Layer 1: COLLECTION    → gather raw data from sources
```

**Build bottom-up.** Each layer depends on the one below it. Never build Layer 3 before Layer 1 works.

---

## The 3 Growth Stages

Within each layer, features evolve through 3 stages:

```
Stage A: Manual       → you do it by hand, scripts are helpers
Stage B: Automated    → scripts do it, you review results
Stage C: Autonomous   → runs on schedule, alerts you when needed
```

**Don't jump to C.** Most projects die trying to automate something they haven't done manually yet.

---

## The Build Sequence

### Phase 1: Collection — Get Raw Data
**Pattern:** Multiple sources → normalize → deduplicate → store

| | Detail |
|---|---|
| **Requirements** | At least one data source accessible (API, scraper, file). A schema for what a "record" looks like. Storage location decided. |
| **Input** | External sources (APIs, websites, feeds, files) + search parameters (keywords, regions, filters) |
| **Expectation** | Raw but structured data. Not clean, not scored — just collected and deduplicated. Quantity over quality at this stage. |
| **Output** | `raw_data.json` — timestamped, deduplicated, with source metadata per record |

| Step | What | Output |
|------|------|--------|
| 1a | One source, manual trigger | `raw_data.json` |
| 1b | Multiple sources, still manual | Merged, deduped JSON |
| 1c | Configurable sources, keywords, regions | Config-driven collection |

**Exit criteria:** You have structured data you can look at and say "this is useful raw material."

**Gate to Phase 2:** Output schema is stable. Adding more sources doesn't change the record format.

**Anti-pattern:** Building 10 sources before validating the data is useful.

---

### Phase 2: Enrichment — Make Data Usable
**Pattern:** Raw data → clean → enrich with external signals → embed for search

| | Detail |
|---|---|
| **Requirements** | Phase 1 output exists and schema is stable. Enrichment sources identified (APIs, full-page fetches, NLP). Embedding model chosen if doing semantic search. |
| **Input** | `raw_data.json` from Phase 1 + external enrichment sources + (optional) reference documents for embeddings (resumes, profiles, knowledge base) |
| **Expectation** | Each record gains enough signal to differentiate good from bad. Not all records need enrichment — prioritize top candidates. |
| **Output** | `enriched_data.json` — original fields + cleaned fields + additional signals. Optionally: vector store with embeddings. |

| Step | What | Output |
|------|------|--------|
| 2a | Clean and normalize fields | Consistent schema |
| 2b | Enrich from external sources | Additional fields (descriptions, metadata) |
| 2c | Embed for semantic search | Vector store, similarity scores |

**Exit criteria:** Each data item has enough signal to make decisions on.

**Gate to Phase 3:** Enriched records have measurably more signal than raw ones. You can manually sort 10 records and the enriched fields help you decide.

**Depends on:** Phase 1 output format is stable.

**Anti-pattern:** Enriching everything. Enrich the top N, validate value, then scale.

---

### Phase 3: Intelligence — Score and Rank
**Pattern:** Enriched data → scoring model → ranked output with explanations

| | Detail |
|---|---|
| **Requirements** | Phase 2 output has enough signal per record. Scoring dimensions identified (what makes a record "good"?). Reference profile exists (what are you matching against?). |
| **Input** | `enriched_data.json` from Phase 2 + scoring config (weights, thresholds, dimensions) + reference profile (your resume, preferences, criteria) |
| **Expectation** | Ranked list where position 1 is genuinely better than position 50. Each record has a score breakdown explaining why. False positives pushed down, true matches promoted. |
| **Output** | `scored_data.json` — original + enriched fields + composite score + per-dimension breakdown + bucket assignment (top/strong/moderate/drop) |

| Step | What | Output |
|------|------|--------|
| 3a | Rule-based scoring (keywords, thresholds) | Simple pass/fail filter |
| 3b | Single-signal scoring (semantic similarity, LLM) | Scored + sorted list |
| 3c | Multi-signal composite scoring | Weighted score with breakdown per dimension |

**Exit criteria:** Top-ranked items are genuinely the best ones. You trust the ranking.

**Gate to Phase 4:** Manual review of top 10 confirms they belong there. Bottom 10 confirms they deserve low scores. The middle is where tuning happens later.

**Depends on:** Phase 2 enrichment quality directly affects scoring accuracy.

**Anti-pattern:** Tuning weights without outcome data. Build Phase 5 (feedback) first.

---

### Phase 4: Action — Do Something With Results
**Pattern:** Ranked data → human review → act → track outcomes

| | Detail |
|---|---|
| **Requirements** | Phase 3 produces a trusted ranking. Action types defined (approve, skip, generate, alert). Outcome tracking schema exists (what happened after acting?). |
| **Input** | `scored_data.json` from Phase 3 + user decisions (approve/skip) + action templates (cover letters, proposals, alerts) |
| **Expectation** | Pipeline saves time vs doing it all manually. Human stays in the loop for high-stakes decisions. Outcomes are recorded for future learning. |
| **Output** | `tracker.json` — acted-upon items with status, dates, follow-ups. Optionally: generated materials (drafts, prep docs). |

| Step | What | Output |
|------|------|--------|
| 4a | Manual review, manual action | You look at results and act |
| 4b | Interactive review with guided actions | Approve/skip UI, auto-imports |
| 4c | Auto-generation (drafts, prep docs, alerts) | Generated materials per item |

**Exit criteria:** The pipeline saves you time compared to doing it all manually.

**Gate to Phase 5:** You have enough tracked outcomes (20-50+) to correlate scores with results. Without outcomes, feedback is guesswork.

**Depends on:** Phase 3 ranking quality — acting on bad rankings wastes effort.

**Anti-pattern:** Auto-acting before you trust the scoring. Keep human-in-the-loop until Phase 5 validates accuracy.

---

### Phase 5: Learning — Feedback and Calibration
**Pattern:** Track outcomes → correlate with scores → adjust model → improve

| | Detail |
|---|---|
| **Requirements** | Phase 4 has accumulated enough outcomes (success/failure per item). Score data preserved per item (which dimensions scored high/low). Enough data points to avoid overfitting (20-50+ outcomes minimum). |
| **Input** | `tracker.json` (outcomes: success, failure, no-response) + historical `scored_data.json` (original scores at time of action) |
| **Expectation** | Discover which scoring dimensions actually predict success. Adjust weights so future runs rank better. Identify blind spots (items scored low that succeeded, or scored high that failed). |
| **Output** | `feedback.json` — outcome correlations, suggested weight adjustments, confidence levels. Updated config with calibrated weights. |

| Step | What | Output |
|------|------|--------|
| 5a | Track outcomes (success/failure per item) | Outcome log |
| 5b | Correlate outcomes with scores | "Score 0.8+ → 40% success rate" |
| 5c | Auto-adjust weights/thresholds based on data | Self-improving pipeline |

**Exit criteria:** The system gets better with use, not just with manual tuning.

**Gate to autonomy:** When feedback-adjusted weights outperform manually-tuned weights over 3+ cycles, the system can start self-tuning.

**Depends on:** Phase 4 outcomes accumulating over time.

**Anti-pattern:** Adjusting on small samples. Need enough data points to be statistically meaningful.

---

## Phase Gate Summary

```
Phase 1 → GATE: Schema stable, data is useful raw material
    ↓
Phase 2 → GATE: Enriched records have measurably more signal
    ↓
Phase 3 → GATE: Top 10 are genuinely best, bottom 10 deserve it
    ↓
Phase 4 → GATE: 20-50+ tracked outcomes accumulated
    ↓
Phase 5 → GATE: Feedback-adjusted weights outperform manual tuning
    ↓
    Autonomous operation
```

Each gate is a checkpoint. Don't proceed until the gate condition is met.
Going back is normal — if Phase 3 ranking is poor, the fix is often in Phase 2 enrichment.

---

## Cross-Cutting Concerns

These aren't phases — they grow alongside the main phases:

### Storage Strategy
```
Phase 1-2: Flat JSON files per run
Phase 3:   + Vector DB for embeddings
Phase 4:   + Persistent state files (trackers)
Phase 5:   + Append-only logs (feedback, trends)
Growth:    When JSON gets slow → SQLite. When SQLite gets complex → Postgres.
```

### Observability
```
Phase 1: Print statements showing counts
Phase 2: Structured summaries (tables, stats)
Phase 3: Score distributions, top-N previews
Phase 4: Decision logging (why this action)
Phase 5: Trend dashboards across runs
```

### Output Organization
```
Early:  Flat timestamped files in one dir
Mid:    Per-run directories with symlink to latest
Late:   Per-run dirs + persistent cross-run DBs + archives
```

### Configuration
```
Early:  Hardcoded constants
Mid:    Config files with sensible defaults
Late:   Config + runtime overrides (CLI flags) + learned adjustments (feedback)
```

---

## Decision Framework

When starting a new feature, ask these in order:

```
1. Which layer? (Collection / Enrichment / Intelligence / Action / Learning)
        ↓
2. Are layers below it solid? → If no, fix the foundation first
        ↓
3. Which stage? (Manual / Automated / Autonomous)
        ↓
4. Has the previous stage been validated? → If no, validate first
        ↓
5. What's the minimal version? → Build that, validate, then expand
```

---

## Example: Mapping This Job Search Project

```
Layer 1 - Collection:     5 scrapers, config-driven        [Phase 1 ✓]
Layer 2 - Enrichment:     Indeed enrichment, embeddings     [Phase 2-3 ✓]
Layer 3 - Intelligence:   Composite scoring, 5 signals      [Phase 4 ✓]
Layer 4 - Action:         Review, track, follow-up          [Phase 5 ✓]
Layer 5 - Learning:       Feedback loop                     [Phase 6 planned]
```

## Example: Applying to a Different Project

**E-commerce price tracker:**
```
Layer 1: Scrape prices from 5 retailers
Layer 2: Normalize currencies, detect variants, link same products
Layer 3: Score deals (price vs history, vs competitors, vs budget)
Layer 4: Alert on good deals, auto-add to cart
Layer 5: Track which alerts led to purchases, tune deal thresholds
```

**Content curation system:**
```
Layer 1: Collect articles from RSS, Twitter, HN, Reddit
Layer 2: Extract topics, embed for similarity, dedup
Layer 3: Score relevance to user interests, rank by novelty
Layer 4: Daily digest email, save to read-later
Layer 5: Track what was actually read, tune interest weights
```

**Freelance lead finder:**
```
Layer 1: Scrape Upwork, Malt, Freelance.com, company RFPs
Layer 2: Parse budgets, timelines, required skills
Layer 3: Score fit against profile, rank by $/hour potential
Layer 4: Generate proposals, track submissions
Layer 5: Win/loss feedback, tune scoring + proposal templates
```

---

## Summary

```
Build bottom-up:     Collection → Enrichment → Intelligence → Action → Learning
Grow stage-by-stage: Manual → Automated → Autonomous
Validate each step:  Don't automate what you haven't done manually
Feedback is king:    Phase 5 improves every other phase retroactively
Storage grows:       JSON → SQLite → external DB (only when needed)
```
