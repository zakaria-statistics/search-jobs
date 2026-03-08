# ML Models for Getting Hired — What, Where, and When

## The Hiring Funnel & Where ML Helps

```
YOUR FUNNEL:                          ML MODEL AT EACH STAGE:
─────────────────────────────────     ──────────────────────────────────

  500 scraped jobs                    ┌─────────────────────────────┐
       │                              │ 1. GHOST CLASSIFIER         │
       ▼                              │    "Is this job real?"      │
  400 after ghost filter              │    Logistic Regression      │
       │                              └─────────────────────────────┘
       ▼                              ┌─────────────────────────────┐
  150 after relevance filter          │ 2. JOB-RESUME MATCHER       │
       │                              │    "Does this match me?"    │
       ▼                              │    Sentence Transformers    │
  80 after blocker filter             │    (already have this!)     │
       │                              └─────────────────────────────┘
       ▼                              ┌─────────────────────────────┐
  30 worth applying to                │ 3. SUCCESS PREDICTOR        │
       │                              │    "Will I get a response?" │
       ▼                              │    Gradient Boosted Trees   │
  10 applications sent                └─────────────────────────────┘
       │                              ┌─────────────────────────────┐
       ▼                              │ 4. RESPONSE OPTIMIZER       │
  3 responses                         │    "Best resume + cover     │
       │                              │     letter for this job?"   │
       ▼                              │    LLM (Claude API)         │
  1 HIRED                             └─────────────────────────────┘
```

---

## Model 1: Ghost Classifier

**Goal:** Filter out fake/ghost listings before you waste time.

### Phase 1 (now): Weighted Heuristic
```
Type:        Weighted linear scorer
Formula:     ghost_score = Σ(signalᵢ × weightᵢ)
Needs:       0 training data
Accuracy:    ~70% estimated (good enough to start)
Already in:  tomorrow's plan (9 signals)
```

### Phase 2 (after ~20 labeled outcomes): Bayesian Weight Updates
```
Type:        Naive Bayes / Bayesian inference
Formula:     P(ghost | signals) = P(signals | ghost) × P(ghost) / P(signals)
Needs:       ~20 labeled examples (enough to start updating beliefs)
Accuracy:    ~75-80% estimated
Why this:    works with VERY small data (even 10 examples help),
             updates incrementally (no full retrain), gives probabilities
             not just scores, mathematically principled

How it works:
  Start with PRIOR beliefs (your hand-tuned weights):
    P(ghost | age > 60 days) = 0.80      ← your initial estimate

  After 20 tracked outcomes, UPDATE with evidence:
    You applied to 5 jobs aged 60+ days → 4 ghosted, 1 responded
    POSTERIOR: P(ghost | age > 60 days) = 0.85   ← evidence says slightly worse

    You applied to 8 agency jobs → 3 ghosted, 5 responded
    POSTERIOR: P(ghost | agency) = 0.45           ← evidence says agencies aren't as bad
    Weight for employer_signal drops from 0.15 → 0.10

  Each new outcome refines the weights automatically.

The math (per signal):
  prior_ghost_rate = 0.22                 ← 22% of all jobs are ghosts (industry data)

  For each signal sᵢ:
    likelihood_ratio = P(sᵢ | ghost) / P(sᵢ | real)

    After N outcomes:
      P(sᵢ | ghost) = count(sᵢ=high AND outcome=ghosted) / count(outcome=ghosted)
      P(sᵢ | real)  = count(sᵢ=high AND outcome=responded) / count(outcome=responded)

    Updated weight ∝ log(likelihood_ratio)
    Signals that discriminate well get higher weights.
    Signals that don't discriminate lose weight.

Code:
  # No library needed — pure Python
  class BayesianGhostDetector:
      def __init__(self, prior_ghost_rate=0.22):
          self.prior = prior_ghost_rate
          self.signal_counts = {
              # signal_name: {ghost: {high: N, low: N}, real: {high: N, low: N}}
          }

      def update(self, signals: dict, outcome: str):
          """outcome = 'ghost' or 'real' (from application tracking)"""
          for name, value in signals.items():
              bucket = 'high' if value > 0.5 else 'low'
              self.signal_counts[name][outcome][bucket] += 1

      def predict(self, signals: dict) -> float:
          """Returns P(ghost | observed signals)"""
          log_odds = math.log(self.prior / (1 - self.prior))
          for name, value in signals.items():
              bucket = 'high' if value > 0.5 else 'low'
              lr = self._likelihood_ratio(name, bucket)
              log_odds += math.log(lr)
          return 1 / (1 + math.exp(-log_odds))

Advantage over jumping straight to LogReg:
  - Works with 10-20 examples (LogReg needs 100+)
  - Updates ONE example at a time (no batch retrain)
  - Degrades gracefully (falls back to prior with no data)
  - Shows exactly WHY weights changed (transparent)
  - Bridges the gap: heuristic → Bayesian → LogReg → GBDT
```

### Phase 3 (after ~100 labeled outcomes): Logistic Regression
```
Type:        sklearn.linear_model.LogisticRegression
Features:    9 ghost signals + application outcome (responded/ghosted)
Needs:       ~100 labeled examples (applied + tracked outcome)
Accuracy:    ~85% estimated
Why this:    interpretable (shows which signals matter), works on small data,
             no GPU needed, trains in <1 second

When to switch from Bayesian:
  Bayesian assumes signals are independent (naive).
  LogReg captures correlations: "agency + old + reposted together = worse than sum"
  When you have 100+ examples, LogReg outperforms naive Bayes.

Code:
  from sklearn.linear_model import LogisticRegression
  model = LogisticRegression()
  model.fit(X_signals, y_ghost_labels)  # y=1 ghost, y=0 real
  # model.coef_ tells you exactly which signals predict ghosts
```

### Phase 4 (after ~500 labeled outcomes): Gradient Boosted Trees
```
Type:        sklearn.ensemble.GradientBoostingClassifier (or LightGBM)
Features:    9 signals + derived features (signal interactions)
Needs:       ~500 labeled examples
Accuracy:    ~90% estimated
Why this:    handles non-linear patterns ("agency + old + reposted" combo),
             still interpretable via feature importance, fast to train

When:        3–6 months of daily scraping + tracking
```

**NOT worth using:** Deep learning, transformers, neural nets — your dataset is too small and the problem is too simple. Logistic regression will likely plateau at 85-90% which is more than enough.

---

## Model 2: Job-Resume Matcher (ALREADY HAVE)

**Goal:** Score how well a job matches your skills and experience.

```
Current:     ChromaDB + all-MiniLM-L6-v2 (sentence-transformers)
             Already computing semantic_score per job
             Already matching against 8 resume variants

This is working. Don't change the model — improve the INPUT:
  - Longer descriptions (500 → 3000 chars) = better embeddings
  - More resume variants = better stack matching
  - Skill extraction from descriptions = explicit match scoring
```

### Possible upgrade (Phase 10+): Cross-Encoder Reranking
```
Type:        cross-encoder/ms-marco-MiniLM-L-6-v2
What:        Takes (resume, job_description) pair → single relevance score
Why better:  Cross-encoders see both texts together (vs separate embeddings)
Accuracy:    ~15% better than bi-encoder for ranking tasks
Cost:        Slower (can't pre-compute), use only on top 50 candidates
When:        Only if current semantic scoring feels inaccurate

Code:
  from sentence_transformers import CrossEncoder
  model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
  scores = model.predict([(resume_text, job_desc) for job_desc in top_50])
```

---

## Model 3: Success Predictor ← HIGHEST IMPACT

**Goal:** Predict probability of getting a response/interview for a specific job.

This is the model that saves you the most time. Instead of applying to 30 jobs and getting 3 responses, apply to 10 high-probability ones and get 3 responses.

### What predicts success (features):

```
FROM JOB:
  - ghost_score (Model 1 output)
  - composite_score (existing)
  - posting_age_days
  - employer_type (direct/agency)
  - description_specificity
  - seniority_alignment
  - location_match
  - blocker_count

FROM YOUR PROFILE vs JOB:
  - skill_overlap_pct (% of required skills you have)
  - experience_gap_years (their requirement - your 5 years)
  - stack_alignment (Azure job + Azure resume = high)
  - title_match_level (exact title vs adjacent role)

FROM HISTORY:
  - company_response_rate (did this company respond before?)
  - source_response_rate (Indeed jobs respond more than RemoteOK?)
  - similar_job_response_rate (DevOps roles → X% response rate for you)
```

### Implementation progression:

**Phase 1 (now): Rule-based estimate**
```
No ML needed yet. Simple formula:

  success_prob = opportunity_score       (from ghost + blocker + fit)
               × source_modifier         (Indeed=1.2, RemoteOK=0.8, etc.)
               × freshness_modifier      (< 3 days = 1.5, > 30 days = 0.5)

This is a rough estimate but better than nothing.
```

**Phase 2 (after ~50 applications): Logistic Regression**
```
Type:        LogisticRegression (same as ghost model)
Target:      y=1 (got response/interview), y=0 (ghosted after 30 days)
Features:    ~15 features from job + profile + history
Needs:       ~50 applications with tracked outcomes
Output:      P(response) per job — rank by this

This is where the feedback loop pays off.
Applied to 50 jobs, tracked outcomes → now the model knows:
  "Jobs with skill_overlap > 0.6 AND posting_age < 7 AND direct_employer
   → 40% response rate"
  "Jobs with skill_overlap < 0.3 OR posting_age > 30
   → 2% response rate"
```

**Phase 3 (after ~200 applications): Gradient Boosted Trees**
```
Type:        LightGBM or XGBoost
Why:         Captures interactions: "high skill overlap + agency = still low response"
Features:    Same 15 + interaction features
Output:      P(response) with confidence interval

Bonus: SHAP explanations per prediction
  "This job has 35% response probability because:
   +0.15 from skill_overlap (0.72)
   +0.10 from posting_age (5 days)
   -0.08 from agency employer
   -0.05 from no_careers_page"
```

---

## Model 4: Response Optimizer (LLM-powered)

**Goal:** For each high-probability job, generate the best application materials.

```
Type:        Claude API (already integrated)
Input:       job description + best-matching resume variant + candidate context
Output:      - tailored cover letter
             - resume bullet point suggestions (reorder/emphasize)
             - interview prep notes (likely questions based on job desc)

This is NOT an ML model to train — it's using Claude as a tool.
Run only on Tier 1/2 jobs (APPLY NOW / WORTH EFFORT).
Cost: ~$0.05 per job (one API call)
```

---

## Model 5 (bonus): Market Intelligence

**Goal:** Understand job market trends to time applications and target skills.

```
Type:        Time series analysis + clustering
Library:     pandas + sklearn.cluster.KMeans

From accumulated scrape data (after 30+ runs):

TREND DETECTION:
  - "Kubernetes mentions increased 20% this month" → hot skill
  - "Azure jobs decreased, AWS jobs increased" → market shift
  - "Remote DevOps postings dropped 15%" → market cooling

SALARY CLUSTERING:
  - Cluster jobs by (skills, location, seniority) → salary bands
  - "Your profile cluster averages €65-80K in Germany"

TIMING:
  - "Tuesday-Wednesday postings get filled 30% faster" → apply on posting day
  - "Jobs posted in Jan/Sep have higher response rates" → hiring seasons

Needs: 30+ runs of data, no training labels needed (unsupervised)
```

---

## Summary: What to Use When

```
┌───────────────────────┬──────────────────────┬────────────┬──────────────┐
│ Model                 │ Algorithm            │ Data needed│ When         │
├───────────────────────┼──────────────────────┼────────────┼──────────────┤
│ Ghost classifier      │ Weighted scorer →    │ 0 → 20 →   │ Tomorrow →   │
│                       │ Bayesian updates →   │ 100 → 500  │ Week 3 →     │
│                       │ LogReg → GBDT        │ outcomes   │ Month 2 → 3  │
├───────────────────────┼──────────────────────┼────────────┼──────────────┤
│ Job-resume matcher    │ Sentence Transformers│ ALREADY    │ ALREADY HAVE │
│                       │ (all-MiniLM-L6-v2)  │ WORKING    │ improve input│
├───────────────────────┼──────────────────────┼────────────┼──────────────┤
│ Success predictor     │ Rules → Bayesian →   │ 0 → 20 →  │ Tomorrow →   │
│                       │ LogReg → LightGBM    │ 50 → 200   │ Month 2-3   │
├───────────────────────┼──────────────────────┼────────────┼──────────────┤
│ Response optimizer    │ Claude API (LLM)     │ 0 (prompt) │ After ghost  │
│                       │                      │            │ filter works │
├───────────────────────┼──────────────────────┼────────────┼──────────────┤
│ Market intelligence   │ Time series +        │ 30+ runs   │ Month 2+    │
│                       │ KMeans clustering    │ (unsuperv.)│              │
└───────────────────────┴──────────────────────┴────────────┴──────────────┘
```

## What NOT To Use

```
❌ Deep neural networks     — dataset too small (<1000 examples)
❌ GPT/LLM for classification — too expensive per job ($0.05 × 500 = $25/run)
❌ Reinforcement learning   — no interactive environment to learn from
❌ GANs                     — not a generation problem
❌ Fine-tuned BERT          — overkill, sentence-transformers already handles it
❌ Collaborative filtering  — you're one user, not a platform
```

## Dependencies (all pip-installable, no GPU needed)

```
Already installed:        sentence-transformers, chromadb, anthropic
Add for Phase 2-3:        scikit-learn (LogReg, GBDT, KMeans)
Optional later:           lightgbm, shap (for explanations)
Never needed:             tensorflow, pytorch, transformers (full)
```
