# LinkedIn Profile Optimizer
## Apify Scraper + Claude API — Personalized for Zakaria Elmoumnaoui

Automatically scrape any LinkedIn profile with Apify, then get AI-powered optimization recommendations from Claude — with your full candidate context (skills, goals, target roles, regions) pre-loaded.

---

## Architecture

```
LinkedIn URL                          Job Search Query
    │                                       │
    ▼                                       ▼
┌─────────────────────┐       ┌─────────────────────────┐
│  Apify Actor         │       │  Apify Actor              │
│  linkedin-profile-   │       │  harvestapi/linkedin-     │
│  scraper             │       │  job-search (~$1/1k jobs) │
└──────────┬──────────┘       └────────────┬────────────┘
           │ JSON                          │ JSON
           └──────────┬────────────────────┘
                      ▼
            ┌─────────────────────┐
            │  Claude API          │  claude-sonnet-4-5 / opus-4-6
            │  + Your Context      │  ← skills, goals, target roles baked in
            │  (analysis engine)   │
            └──────────┬──────────┘
                       │
                 ┌─────┴─────┐
                 ▼           ▼
              JSON      Markdown
              Report      Report
```

## Three Modes

| Mode | Purpose | Command |
|------|---------|---------|
| `self` | Optimize YOUR profile | `--mode self` (default) |
| `competitor` | Reverse-engineer a competitor's profile | `--mode competitor` |
| `jobs` | Search & rank LinkedIn jobs by fit | `--mode jobs -q "DevOps Engineer" -l "France"` |

---

## Quick Start

### 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install apify-client anthropic python-dotenv rich
```

(`rich` is optional — adds colored console output)

> **Note:** All `python` commands below assume the venv is activated. Alternatively, use `./venv/bin/python` directly.

### 2. API Keys

Create `.env`:

```env
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

- Apify: [console.apify.com/account#/integrations](https://console.apify.com/account#/integrations)
- Anthropic: [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

### 3. Run

```bash
# Scrape + analyze your profile
python linkedin_optimizer.py --url "https://www.linkedin.com/in/zakariaelmoumnaoui/"

# With Markdown report
python linkedin_optimizer.py --url "https://www.linkedin.com/in/zakariaelmoumnaoui/" --md

# Save scrape for reuse (no Apify cost on re-runs)
python linkedin_optimizer.py \
  --url "https://www.linkedin.com/in/zakariaelmoumnaoui/" \
  --save-profile my_profile.json

# Re-analyze from saved scrape
python linkedin_optimizer.py --file my_profile.json --md

# Analyze a competitor
python linkedin_optimizer.py \
  --url "https://www.linkedin.com/in/senior-devops-in-france/" \
  --mode competitor

# Override target role
python linkedin_optimizer.py --file my_profile.json --target-role "Platform Engineer"

# Use Opus for deeper analysis
python linkedin_optimizer.py --file my_profile.json --model claude-opus-4-6 --md
```

#### Job Search Mode

```bash
# Search DevOps jobs in France
python linkedin_optimizer.py --mode jobs --query "DevOps Engineer" --location "France"

# Remote cloud jobs with markdown report
python linkedin_optimizer.py --mode jobs -q "Cloud Engineer" -l "London" --workplace-type remote --md

# Filter by experience level and employment type
python linkedin_optimizer.py --mode jobs -q "SRE" -l "Germany" \
  --experience-level mid-senior --employment-type fulltime --md

# Limit results and save raw jobs for re-analysis
python linkedin_optimizer.py --mode jobs -q "Platform Engineer" -l "Netherlands" \
  --max-jobs 10 --save-profile jobs.json

# Re-analyze saved jobs without calling Apify again
python linkedin_optimizer.py --mode jobs --job-file jobs.json --md
```

---

## What You Get

### Self Mode (`--mode self`)
- Profile scores (0–100) across 8 dimensions
- Critical issues with specific fixes
- 3 headline options targeting different search strategies
- Full About section rewrite (Math → DevOps → Cloud story)
- Experience bullet rewrites with metrics and keywords
- Skills optimization (pin, add, remove)
- Keyword gap analysis vs. real EU/France job postings
- Quick wins sorted by impact/effort
- Content strategy (topics, hashtags, frequency)
- Competitor differentiation advice

### Competitor Mode (`--mode competitor`)
- Competitor strengths/weaknesses breakdown
- Lessons to steal (with where to apply them)
- Keywords they use that you don't
- Structural patterns to adopt
- Differentiation opportunities

### Jobs Mode (`--mode jobs`)
- Each job scored 0–100 on: skills match, experience fit, location fit, growth potential
- Weighted overall fit score (skills 40%, experience 30%, location 15%, growth 15%)
- Ranked table of all jobs with priority labels (apply now / strong match / worth trying / long shot / skip)
- Per-job breakdown: matching skills, missing skills, resume tweaks
- Global insights: most demanded skills, skills to learn, market observations, search refinements

---

## Files

| File | Purpose |
|------|---------|
| `linkedin_optimizer.py` | Full automation script |
| `linkedin_optimization_prompt.md` | Standalone prompt template (for API or manual use) |
| `README.md` | This file |

---

## Cost Estimate

| Component | Cost |
|-----------|------|
| Apify profile scrape | ~$0.01–0.05 per profile |
| Apify job search (HarvestAPI) | ~$1.00 per 1,000 jobs |
| Claude Sonnet | ~$0.03–0.10 per analysis |
| Claude Opus | ~$0.15–0.50 per analysis |

**Tip:** Use `--save-profile` on the first run, then `--file` / `--job-file` for iterations to avoid re-scraping.

---

## Workflow Recommendation

1. **First run:** Scrape + save + analyze with Sonnet
   ```bash
   python linkedin_optimizer.py --url "YOUR_URL" --save-profile profile.json --md
   ```

2. **Deep analysis:** Re-run with Opus on saved data
   ```bash
   python linkedin_optimizer.py --file profile.json --model claude-opus-4-6 --md
   ```

3. **Competitor research:** Scrape 2–3 strong profiles in your target market
   ```bash
   python linkedin_optimizer.py --url "COMPETITOR_URL" --mode competitor -o competitor1.json
   ```

4. **Apply changes** to your LinkedIn profile

5. **Re-scrape + re-analyze** after changes to measure improvement

6. **Job search:** Find matching roles and prioritize applications
   ```bash
   python linkedin_optimizer.py --mode jobs -q "DevOps Engineer" -l "France" --save-profile jobs.json --md
   ```

7. **Re-rank saved jobs** after updating your skills
   ```bash
   python linkedin_optimizer.py --mode jobs --job-file jobs.json --md
   ```