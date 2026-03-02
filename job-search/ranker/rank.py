"""Core ranking logic: load scraped jobs, pre-filter, send to Claude, save results."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from . import config
from .config import (
    ANTHROPIC_KEY,
    JOB_FIELDS_FOR_RANKING,
    JOB_DESC_TRUNCATE,
    CANDIDATE_SKILL_KEYWORDS,
    CLAUDE_MAX_TOKENS,
)
from .prompts import SYSTEM_PROMPT_JOBS


def log(msg: str):
    print(f"  {msg}")


def load_scraped_jobs(filepath: str) -> list[dict]:
    """Load jobs from a scraper output JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("jobs", [])


def pre_filter_jobs(jobs: list[dict]) -> list[dict]:
    """Drop jobs that have zero keyword overlap with candidate skills."""
    filtered = []
    for job in jobs:
        text = (
            (job.get("title") or "") + " " +
            (job.get("description") or "")
        ).lower()
        if any(kw in text for kw in CANDIDATE_SKILL_KEYWORDS):
            filtered.append(job)
    dropped = len(jobs) - len(filtered)
    if dropped:
        log(f"Pre-filter: dropped {dropped} irrelevant jobs, keeping {len(filtered)}")
    return filtered


def slim_job(job: dict) -> dict:
    """Strip heavy fields and truncate description to save tokens."""
    slim = {}
    for key in JOB_FIELDS_FOR_RANKING:
        if key in job:
            slim[key] = job[key]
    desc = job.get("description") or ""
    if len(desc) > JOB_DESC_TRUNCATE:
        slim["description"] = desc[:JOB_DESC_TRUNCATE] + "..."
    else:
        slim["description"] = desc
    return slim


def rank_jobs(jobs: list[dict], target_role: str = None) -> dict:
    """Send job listings to Claude for ranked analysis against candidate profile."""
    if not ANTHROPIC_KEY:
        print("ANTHROPIC_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    # Pre-filter and slim
    relevant = pre_filter_jobs(jobs)
    if not relevant:
        print("No relevant jobs after filtering. Try broader search terms.")
        return {"ranked_jobs": [], "search_summary": {"total_jobs_analyzed": 0}}

    slim_jobs = [slim_job(j) for j in relevant]

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    jobs_json = json.dumps(slim_jobs, indent=2, default=str)

    user_msg = f"""Analyze and rank the following {len(slim_jobs)} job postings for fit against the candidate profile in the system prompt.

{"Target role focus: " + target_role if target_role else ""}

## Job Listings Data

{jobs_json}

---

Instructions:
1. Score every job honestly across all 4 dimensions
2. Rank by overall fit score (descending)
3. Be specific about which skills match and which are missing
4. Resume tweaks should be actionable one-liners
5. Priority labels should reflect realistic chances
6. Global insights should help refine the job search strategy"""

    log(f"Analyzing {len(slim_jobs)} jobs with {config.CLAUDE_MODEL}...")
    start = time.time()

    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=SYSTEM_PROMPT_JOBS,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        print(f"Claude API error: {e}")
        sys.exit(1)

    elapsed = time.time() - start
    usage = response.usage
    log(f"Done in {elapsed:.1f}s ({usage.input_tokens} in / {usage.output_tokens} out)")

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log("Response wasn't valid JSON -- saving raw text")
        return {"raw_response": raw}


def save_ranked(ranked_data: dict, output_dir: str = None) -> str:
    """Save ranked results to a daily JSON file."""
    if output_dir is None:
        output_dir = str(Path(__file__).parent.parent / "output")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filepath = str(Path(output_dir) / f"ranked_{today}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(ranked_data, f, indent=2, ensure_ascii=False)

    return filepath
