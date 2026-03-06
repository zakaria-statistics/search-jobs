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
    USE_SEMANTIC_FILTER,
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
    """Strip heavy fields and extract skill-relevant description sentences."""
    from scraper.description_utils import extract_skill_sentences

    slim = {}
    for key in JOB_FIELDS_FOR_RANKING:
        if key in job:
            slim[key] = job[key]
    desc = job.get("description") or ""
    if len(desc) > JOB_DESC_TRUNCATE:
        # Extract skill-relevant sentences instead of blind truncation
        skill_desc = extract_skill_sentences(desc, max_chars=JOB_DESC_TRUNCATE)
        slim["description"] = skill_desc if skill_desc else desc[:JOB_DESC_TRUNCATE] + "..."
    else:
        slim["description"] = desc

    # Attach RAG context if available from semantic filter
    if job.get("relevant_chunks"):
        from .semantic_filter import get_rag_context
        rag_ctx = get_rag_context(job)
        if rag_ctx:
            slim["resume_context"] = rag_ctx
    if job.get("semantic_score"):
        slim["semantic_score"] = job["semantic_score"]
    if job.get("matched_stack"):
        slim["matched_stack"] = job["matched_stack"]

    return slim


def prepare_jobs(jobs: list[dict]) -> list[dict]:
    """Slim jobs for Claude — this is exactly what gets sent to the API.

    Call this separately to inspect the payload before spending API tokens.
    """
    return [slim_job(j) for j in jobs]


BATCH_SIZE = 30  # Max jobs per Claude API call (~250 output tokens per job)


def _call_claude(client, slim_jobs: list[dict], target_role: str = None, batch_label: str = "") -> dict:
    """Single Claude API call for a batch of jobs. Returns parsed JSON or error dict."""
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

    payload_chars = len(jobs_json)
    log(f"{batch_label}Sending {len(slim_jobs)} jobs (~{payload_chars // 4:,} tokens in, {CLAUDE_MAX_TOKENS:,} max out)")
    log(f"{batch_label}Streaming response...")
    start = time.time()

    try:
        collected = []

        with client.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=SYSTEM_PROMPT_JOBS,
            messages=[{"role": "user", "content": user_msg}],
        ) as stream:
            last_report = 0
            for text in stream.text_stream:
                collected.append(text)
                current_len = sum(len(t) for t in collected)
                if current_len - last_report >= 2000:
                    elapsed_so_far = time.time() - start
                    est_tokens = current_len // 4
                    print(f"\r  {batch_label}Receiving... {est_tokens:,} tokens (~{elapsed_so_far:.0f}s)", end="", flush=True)
                    last_report = current_len

            final_message = stream.get_final_message()
            input_tokens = final_message.usage.input_tokens if final_message.usage else 0
            output_tokens = final_message.usage.output_tokens if final_message.usage else 0

        print()
    except Exception as e:
        print(f"\n  {batch_label}Claude API error: {e}")
        return None

    elapsed = time.time() - start
    raw = "".join(collected).strip()
    log(f"{batch_label}Done in {elapsed:.1f}s ({input_tokens} in / {output_tokens} out)")

    stop_reason = getattr(final_message, "stop_reason", None)
    if stop_reason == "max_tokens":
        log(f"{batch_label}WARNING: Truncated — hit {CLAUDE_MAX_TOKENS} token limit")

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log(f"{batch_label}Response wasn't valid JSON ({len(raw)} chars, stop: {stop_reason})")
        return None


def _merge_results(batch_results: list[dict]) -> dict:
    """Merge multiple batch results into one ranked output, re-ranked globally by overall score."""
    all_jobs = []
    all_insights = {"most_demanded_skills": [], "skills_to_learn": [],
                    "market_observations": [], "recommended_search_refinements": []}

    for result in batch_results:
        if not result:
            continue
        all_jobs.extend(result.get("ranked_jobs", []))
        insights = result.get("global_insights", {})
        for key in all_insights:
            all_insights[key].extend(insights.get(key, []))

    # Re-rank globally by overall score
    all_jobs.sort(key=lambda j: j.get("scores", {}).get("overall", 0), reverse=True)
    for i, job in enumerate(all_jobs, 1):
        job["rank"] = i

    # Deduplicate insights
    for key in all_insights:
        all_insights[key] = list(dict.fromkeys(all_insights[key]))

    # Compute merged summary
    scores = [j.get("scores", {}).get("overall", 0) for j in all_jobs]
    summary = {
        "total_jobs_analyzed": len(all_jobs),
        "average_fit_score": round(sum(scores) / len(scores)) if scores else 0,
        "top_fit_score": max(scores) if scores else 0,
        "score_distribution": {
            "excellent_80_plus": sum(1 for s in scores if s >= 80),
            "good_60_79": sum(1 for s in scores if 60 <= s < 80),
            "fair_40_59": sum(1 for s in scores if 40 <= s < 60),
            "poor_below_40": sum(1 for s in scores if s < 40),
        },
    }

    return {
        "search_summary": summary,
        "ranked_jobs": all_jobs,
        "global_insights": all_insights,
    }


def rank_jobs(jobs: list[dict], target_role: str = None, skip_filter: bool = False, prepared: bool = False) -> dict:
    """Send job listings to Claude for ranked analysis against candidate profile.

    If prepared=True, jobs are already slimmed (from prepare command) — send as-is.
    Auto-batches into groups of BATCH_SIZE to avoid token limits.
    """
    if not ANTHROPIC_KEY:
        print("ANTHROPIC_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    if prepared:
        log(f"Using pre-prepared input: {len(jobs)} jobs")
        slim_jobs = jobs
    else:
        if skip_filter:
            log(f"Skipping filter (pre-filtered input): {len(jobs)} jobs")
            relevant = jobs
        elif USE_SEMANTIC_FILTER:
            try:
                from .semantic_filter import semantic_filter_jobs
                relevant = semantic_filter_jobs(jobs)
            except Exception as e:
                log(f"Semantic filter failed ({e}), using keyword filter")
                relevant = pre_filter_jobs(jobs)
        else:
            relevant = pre_filter_jobs(jobs)
        if not relevant:
            print("No relevant jobs after filtering. Try broader search terms.")
            return {"ranked_jobs": [], "search_summary": {"total_jobs_analyzed": 0}}

        slim_jobs = prepare_jobs(relevant)

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Split into batches
    batches = [slim_jobs[i:i + BATCH_SIZE] for i in range(0, len(slim_jobs), BATCH_SIZE)]
    total_batches = len(batches)

    log(f"Analyzing {len(slim_jobs)} jobs with {config.CLAUDE_MODEL}...")
    if total_batches > 1:
        log(f"Split into {total_batches} batches of ~{BATCH_SIZE} jobs each")

    start_total = time.time()
    batch_results = []

    for idx, batch in enumerate(batches, 1):
        label = f"[{idx}/{total_batches}] " if total_batches > 1 else ""
        result = _call_claude(client, batch, target_role=target_role, batch_label=label)
        if result:
            batch_results.append(result)
        else:
            log(f"{label}Batch failed — skipping {len(batch)} jobs")

    if not batch_results:
        print("All batches failed. No results.")
        return {"ranked_jobs": [], "search_summary": {"total_jobs_analyzed": 0}}

    elapsed_total = time.time() - start_total

    # Merge if multiple batches, otherwise return single result
    if len(batch_results) == 1:
        merged = batch_results[0]
    else:
        log(f"Merging {len(batch_results)} batch results and re-ranking globally...")
        merged = _merge_results(batch_results)

    log(f"Total time: {elapsed_total:.1f}s for {len(slim_jobs)} jobs")
    return merged


def save_ranked(ranked_data: dict, output_dir: str = None, run_dir: str = None) -> str:
    """Save ranked results to a JSON file.

    If run_dir is provided, saves as {run_dir}/ranked.json (no timestamp in name).
    Otherwise falls back to legacy timestamped filename in output_dir.
    """
    if run_dir is not None:
        Path(run_dir).mkdir(parents=True, exist_ok=True)
        filepath = str(Path(run_dir) / "ranked.json")
    else:
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent / "output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        now_stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filepath = str(Path(output_dir) / f"ranked_{now_stamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(ranked_data, f, indent=2, ensure_ascii=False)

    return filepath
