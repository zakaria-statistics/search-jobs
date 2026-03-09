#!/usr/bin/env python3
"""
pipeline.py — Unified job search pipeline: scrape → rank → review → track.

Usage:
    python scripts/pipeline.py scrape          # Run all scrapers
    python scripts/pipeline.py scrape --sources indeed remoteok
    python scripts/pipeline.py index           # Index resumes into ChromaDB
    python scripts/pipeline.py index --force   # Force reindex even if unchanged
    python scripts/pipeline.py validate        # Check URLs for closed/expired postings
    python scripts/pipeline.py rank            # Rank latest scraped file with Claude
    python scripts/pipeline.py rank --file output/scraped_2026-03-02.json
    python scripts/pipeline.py review          # Interactive: show ranked jobs, approve/skip
    python scripts/pipeline.py run             # Full pipeline: scrape → validate → rank → review
    python scripts/pipeline.py run --skip-validate  # Skip URL validation
    python scripts/pipeline.py manual          # Add a job manually (delegates to tracker)
    python scripts/pipeline.py status          # Show pipeline stats
    python scripts/pipeline.py sync            # Sync output/latest to Google Drive
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env before any module that reads env vars
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ensure job-search/ is on the path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "output"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

RUNS_DIR = OUTPUT_DIR / "runs"


def _create_run_dir(timestamp: str = None) -> Path:
    """Create output/runs/{timestamp}/ and update output/latest symlink.

    Returns the Path to the new run directory.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # Atomic symlink update: create temp symlink then rename over old one
    latest = OUTPUT_DIR / "latest"
    rel_target = Path("runs") / timestamp
    tmp_link = OUTPUT_DIR / f".latest_tmp_{os.getpid()}"
    try:
        tmp_link.symlink_to(rel_target)
        tmp_link.rename(latest)
    except OSError:
        # Fallback: remove then create
        latest.unlink(missing_ok=True)
        latest.symlink_to(rel_target)
        tmp_link.unlink(missing_ok=True)

    return run_dir


# ─── Scrape ──────────────────────────────────────────────────────────────────

AVAILABLE_SCRAPERS = {
    "indeed": "scraper.IndeedScraper",
    "remoteok": "scraper.RemoteOKScraper",
    "arbeitnow": "scraper.ArbeitnowScraper",
    "rekrute": "scraper.RekruteScraper",
    "wttj": "scraper.WTTJScraper",
    "linkedin": "scraper.LinkedInScraper",
}


def cmd_scrape(args):
    """Run scrapers and save results."""
    from scraper import IndeedScraper, RemoteOKScraper, ArbeitnowScraper, RekruteScraper, WTTJScraper, LinkedInScraper
    from scraper.config import KEYWORDS
    from scraper.storage import save_jobs, print_summary

    scraper_map = {
        "indeed": IndeedScraper,
        "remoteok": RemoteOKScraper,
        "arbeitnow": ArbeitnowScraper,
        "rekrute": RekruteScraper,
        "wttj": WTTJScraper,
        "linkedin": LinkedInScraper,
    }

    sources = args.sources if args.sources else list(scraper_map.keys())
    keywords = args.keywords if args.keywords else KEYWORDS
    max_pages = args.max_pages
    regions = args.regions if args.regions else []

    all_jobs = []
    for source in sources:
        if source not in scraper_map:
            logger.warning(f"Unknown source: {source}. Available: {', '.join(scraper_map)}")
            continue
        logger.info(f"Running {source} scraper...")
        try:
            scraper = scraper_map[source]()
            jobs = scraper.scrape(keywords=keywords, regions=regions, max_pages=max_pages)
            all_jobs.extend(jobs)
            logger.info(f"  {source}: {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"  {source} failed: {e}")

    if all_jobs:
        run_dir = getattr(args, "_run_dir", None) or _create_run_dir()
        args._run_dir = run_dir
        filepath = save_jobs(all_jobs, str(OUTPUT_DIR), run_dir=str(run_dir))
        print_summary(all_jobs)
        print(f"Saved {len(all_jobs)} jobs to {filepath}")
    else:
        print("No jobs found across any source.")

    return all_jobs


# ─── Enrich ───────────────────────────────────────────────────────────────────

def cmd_enrich(args):
    """Enrich Indeed jobs with full descriptions."""
    from scraper import IndeedScraper

    if args.file:
        filepath = Path(args.file)
    else:
        filepath = _find_latest_file("scraped_")
        if not filepath:
            print("No scraped files found. Run 'scrape' first.")
            sys.exit(1)

    print(f"Loading jobs from {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", []) if isinstance(data, dict) else data

    indeed_jobs = [j for j in jobs if j.get("source") == "indeed"]
    if not indeed_jobs:
        print("No Indeed jobs found to enrich.")
        return jobs

    max_enrich = args.max_enrich if hasattr(args, "max_enrich") else 50
    print(f"Enriching up to {max_enrich} Indeed jobs...")

    scraper = IndeedScraper()
    scraper.enrich(jobs, max_jobs=max_enrich)

    # Save back
    if isinstance(data, dict):
        data["jobs"] = jobs
    else:
        data = jobs

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    enriched_count = sum(
        1 for j in jobs
        if j.get("source") == "indeed" and len(j.get("description", "")) >= 100
    )
    print(f"Enrichment done. {enriched_count} Indeed jobs now have descriptions.")
    return jobs


# ─── Index ───────────────────────────────────────────────────────────────────

def cmd_index(args):
    """Index resumes into ChromaDB vector store."""
    from ranker.config import (
        CHROMADB_DIR, RESUMES_DIR, CANDIDATE_CONTEXT,
        SEMANTIC_MODEL_NAME, HF_API_TOKEN,
    )
    from ranker.vectorstore import full_index

    force = getattr(args, "force", False)
    print(f"Indexing resumes from {RESUMES_DIR} into {CHROMADB_DIR}...")

    try:
        total = full_index(
            chromadb_dir=CHROMADB_DIR,
            resumes_dir=RESUMES_DIR,
            candidate_context=CANDIDATE_CONTEXT,
            model_name=SEMANTIC_MODEL_NAME,
            hf_token=HF_API_TOKEN,
            force=force,
        )
        if total > 0:
            print(f"Indexed {total} chunks into ChromaDB.")
        else:
            print("Vector store already up-to-date (use --force to reindex).")
    except ImportError as e:
        print(f"Cannot index: {e}")
        print("Install dependencies: pip install chromadb sentence-transformers")
        sys.exit(1)


# ─── Filter (Semantic Pre-filter) ─────────────────────────────────────────────

SCORE_BUCKETS = [
    ("top",      0.75, 1.01, "Best composite matches — send to Claude first"),
    ("strong",   0.60, 0.75, "Good composite matches — worth ranking"),
    ("moderate", 0.45, 0.60, "Partial matches — rank if top bucket is thin"),
]


def _bucket_jobs(filtered: list[dict]) -> dict[str, list[dict]]:
    """Split filtered jobs into score-based buckets using composite score."""
    buckets = {name: [] for name, _, _, _ in SCORE_BUCKETS}
    for j in filtered:
        score = j.get("composite_score", j.get("semantic_score", 0))
        for name, lo, hi, _ in SCORE_BUCKETS:
            if lo <= score < hi:
                buckets[name].append(j)
                break
    return buckets


def cmd_filter(args):
    """Run semantic filter only — no Claude API call. Saves jobs in score buckets."""
    from ranker.rank import load_scraped_jobs

    if args.file:
        filepath = Path(args.file)
    else:
        filepath = _find_latest_file("scraped_")
        if not filepath:
            print("No scraped files found. Run 'scrape' first.")
            sys.exit(1)

    print(f"Loading jobs from {filepath}...")
    jobs = load_scraped_jobs(str(filepath))
    if not jobs:
        print("No jobs found in file.")
        sys.exit(1)

    print(f"Loaded {len(jobs)} jobs. Running semantic filter...")

    threshold = args.threshold if hasattr(args, "threshold") and args.threshold else None

    try:
        from ranker.semantic_filter import semantic_filter_jobs
        filtered = semantic_filter_jobs(jobs, threshold=threshold)
    except Exception as e:
        print(f"Semantic filter failed: {e}")
        print("Falling back to keyword pre-filter...")
        from ranker.rank import pre_filter_jobs
        filtered = pre_filter_jobs(jobs)

    if not filtered:
        print("No jobs passed the filter.")
        return

    # Bucket by score
    buckets = _bucket_jobs(filtered)

    # Show breakdown
    print(f"\n{'='*60}")
    print(f"  SEMANTIC FILTER RESULTS")
    print(f"{'='*60}")
    print(f"  Input:    {len(jobs)} jobs")
    print(f"  Kept:     {len(filtered)} jobs")
    print(f"  Dropped:  {len(jobs) - len(filtered)} jobs")

    # Score buckets
    print(f"\n  Score buckets:")
    for name, lo, hi, desc in SCORE_BUCKETS:
        count = len(buckets[name])
        bar = "#" * min(count, 40)
        print(f"    {name:>8} ({lo:.2f}-{hi:.2f}): {count:>4} jobs  {bar}")
        print(f"             {desc}")

    # By matched stack
    stacks = {}
    for j in filtered:
        s = j.get("matched_stack", "unknown")
        stacks[s] = stacks.get(s, 0) + 1
    print(f"\n  By matched stack:")
    for stack, count in sorted(stacks.items(), key=lambda x: -x[1]):
        print(f"    {stack}: {count}")

    # By source
    sources = {}
    for j in filtered:
        s = j.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    print(f"\n  By source:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")

    # Composite score stats
    c_scores = [j.get("composite_score", 0) for j in filtered]
    s_scores = [j.get("semantic_score", 0) for j in filtered]
    if c_scores:
        print(f"\n  Composite scores:")
        print(f"    Best:  {max(c_scores):.3f}")
        print(f"    Worst: {min(c_scores):.3f}")
        print(f"    Avg:   {sum(c_scores)/len(c_scores):.3f}")
        print(f"  Semantic scores (sub-signal):")
        print(f"    Best:  {max(s_scores):.3f}")
        print(f"    Worst: {min(s_scores):.3f}")
        print(f"    Avg:   {sum(s_scores)/len(s_scores):.3f}")

    # Top 10 preview with breakdown
    print(f"\n  Top 10 by composite score:")
    print(f"    {'Comp':>5} {'Sem':>5} {'Skill':>5} {'Title':>5} {'Loc':>5} {'Stack':>5}  Job")
    print(f"    {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*5}  {'─'*40}")
    for j in filtered[:10]:
        cs = j.get("composite_score", 0)
        bd = j.get("score_breakdown", {})
        print(
            f"    {cs:.2f}  {bd.get('semantic', 0):.2f}  {bd.get('skill_match', 0):.2f}  "
            f"{bd.get('title_match', 0):.2f}  {bd.get('location_match', 0):.2f}  "
            f"{bd.get('stack_depth', 0):.2f}  "
            f"{j.get('title', '?')[:35]} @ {j.get('company', '?')[:15]}"
        )

    print(f"{'='*60}")

    # Determine run dir: use the one from the source scraped file, or create a new one
    run_dir = getattr(args, "_run_dir", None)
    if run_dir is None:
        # Check if source file is inside a run dir
        if RUNS_DIR in filepath.resolve().parents:
            run_dir = filepath.resolve().parent
        else:
            run_dir = _create_run_dir()
        args._run_dir = run_dir

    # Save each bucket as a separate file
    from ranker.relevance import build_relevance

    saved_files = []
    for name, lo, hi, desc in SCORE_BUCKETS:
        bucket_jobs = buckets[name]
        if not bucket_jobs:
            continue
        outpath = Path(run_dir) / f"filtered_{name}.json"
        data = {
            "filtered_at": datetime.now().isoformat(),
            "source_file": str(filepath),
            "bucket": name,
            "score_range": f"{lo:.2f}-{hi:.2f}",
            "total_input": len(jobs),
            "total_in_bucket": len(bucket_jobs),
            "relevance": build_relevance(bucket_jobs, "filtered"),
            "jobs": bucket_jobs,
        }
        outpath.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        saved_files.append((name, len(bucket_jobs), outpath))

    print(f"\nSaved {len(saved_files)} bucket files:")
    for name, count, path in saved_files:
        print(f"  {name:>8}: {count:>4} jobs → {path.name}")

    # Show weight config for transparency
    from ranker.config import COMPOSITE_WEIGHTS
    print(f"\n  Composite weights: {COMPOSITE_WEIGHTS}")

    print(f"\nTo rank a specific bucket:")
    if saved_files:
        print(f"  python scripts/pipeline.py rank --file {saved_files[0][2]}")

    return filtered


# ─── Validate (URL Liveness) ──────────────────────────────────────────────

def cmd_validate(args):
    """Check job URLs for closed/expired postings. Saves validated.json and closed.json."""
    from scraper.url_validator import validate_jobs, drop_closed
    from scraper.config import URL_VALIDATE_DELAY_MIN, URL_VALIDATE_DELAY_MAX, URL_VALIDATE_MAX_JOBS
    from ranker.rank import load_scraped_jobs

    if args.file:
        filepath = Path(args.file)
    else:
        # Prefer filtered_top, then filtered_strong, then scraped
        filepath = _find_latest_file("filtered_top_")
        if filepath:
            print(f"Found top-bucket file: {filepath.name}")
        elif _find_latest_file("filtered_strong_"):
            filepath = _find_latest_file("filtered_strong_")
            print(f"Found strong-bucket file: {filepath.name}")
        else:
            filepath = _find_latest_file("scraped_")
        if not filepath:
            print("No filtered or scraped files found. Run 'filter' or 'scrape' first.")
            sys.exit(1)

    print(f"Loading jobs from {filepath}...")
    jobs = load_scraped_jobs(str(filepath))
    if not jobs:
        print("No jobs found in file.")
        sys.exit(1)

    max_validate = getattr(args, "max_validate", URL_VALIDATE_MAX_JOBS) or URL_VALIDATE_MAX_JOBS
    recheck = getattr(args, "recheck", False)
    delay_min = URL_VALIDATE_DELAY_MIN
    delay_max = URL_VALIDATE_DELAY_MAX

    print(f"Validating up to {max_validate} URLs (recheck={recheck})...")
    validate_jobs(jobs, delay_min=delay_min, delay_max=delay_max,
                  max_jobs=max_validate, recheck=recheck)

    live, closed = drop_closed(jobs)

    # Summary
    unchecked = sum(1 for j in live if not j.get("url_status"))
    print(f"\n{'='*60}")
    print(f"  URL VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"  Total:     {len(jobs)}")
    print(f"  Live:      {len(live)}")
    print(f"  Closed:    {len(closed)}")
    print(f"  Unchecked: {unchecked}")
    if closed:
        print(f"\n  Closed jobs:")
        for j in closed[:10]:
            print(f"    [{j.get('url_status', '?'):>9}] {j.get('title', '?')[:40]} @ {j.get('company', '?')[:15]}")
        if len(closed) > 10:
            print(f"    ... and {len(closed) - 10} more")
    print(f"{'='*60}")

    # Determine run dir
    run_dir = getattr(args, "_run_dir", None)
    if run_dir is None:
        if RUNS_DIR in filepath.resolve().parents:
            run_dir = filepath.resolve().parent
        else:
            run_dir = _create_run_dir()
        args._run_dir = run_dir

    # Save validated.json (live jobs)
    from ranker.relevance import build_relevance

    validated_path = Path(run_dir) / "validated.json"
    validated_data = {
        "validated_at": datetime.now().isoformat(),
        "source_file": str(filepath),
        "total_input": len(jobs),
        "total_live": len(live),
        "total_closed": len(closed),
        "relevance": build_relevance(live, "validated"),
        "jobs": live,
    }
    validated_path.write_text(json.dumps(validated_data, indent=2, ensure_ascii=False, default=str))
    print(f"\nSaved {len(live)} live jobs to {validated_path.name}")

    # Save closed.json (dropped jobs)
    if closed:
        closed_path = Path(run_dir) / "closed.json"
        closed_data = {
            "validated_at": datetime.now().isoformat(),
            "source_file": str(filepath),
            "total_closed": len(closed),
            "jobs": closed,
        }
        closed_path.write_text(json.dumps(closed_data, indent=2, ensure_ascii=False, default=str))
        print(f"Saved {len(closed)} closed jobs to {closed_path.name}")

    return live


# ─── Rank ────────────────────────────────────────────────────────────────────

def _find_latest_file(prefix: str) -> Path | None:
    """Find the most recent file matching prefix.

    Search order:
    1. output/latest/{name}.json  (run-dir style, e.g. "scraped" for prefix "scraped_")
    2. output/runs/*/{name}.json  (scan all run dirs, sorted by dir name descending)
    3. output/{prefix}*.json      (legacy flat files)
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Derive the run-dir filename from the prefix (e.g. "scraped_" -> "scraped.json",
    # "filtered_top_" -> "filtered_top.json")
    run_name = prefix.rstrip("_") + ".json"

    # 1. Check output/latest/ symlink
    latest_dir = OUTPUT_DIR / "latest"
    if latest_dir.is_symlink() or latest_dir.is_dir():
        candidate = latest_dir / run_name
        if candidate.exists():
            return candidate.resolve()

    # 2. Scan output/runs/*/
    if RUNS_DIR.is_dir():
        run_dirs = sorted(RUNS_DIR.iterdir(), reverse=True)
        for rd in run_dirs:
            if rd.is_dir():
                candidate = rd / run_name
                if candidate.exists():
                    return candidate

    # 3. Legacy flat files in output/
    files = sorted(OUTPUT_DIR.glob(f"{prefix}*.json"), reverse=True)
    return files[0] if files else None


# ─── Prepare (Slim for Claude) ─────────────────────────────────────────────

def cmd_prepare(args):
    """Slim filtered jobs into exactly what Claude will receive. Saves prepared.json for inspection."""
    from ranker.rank import load_scraped_jobs, prepare_jobs

    if args.file:
        filepath = Path(args.file)
    else:
        # Prefer validated (URL-checked), then filtered, then scraped
        filepath = _find_latest_file("validated_")
        if filepath:
            print(f"Found validated file: {filepath.name}")
        else:
            filepath = _find_latest_file("filtered_top_")
            if filepath:
                print(f"Found top-bucket file: {filepath.name}")
            elif _find_latest_file("filtered_strong_"):
                filepath = _find_latest_file("filtered_strong_")
                print(f"Found strong-bucket file: {filepath.name}")
            else:
                filepath = _find_latest_file("scraped_")
        if not filepath:
            print("No validated, filtered, or scraped files found. Run 'validate', 'filter', or 'scrape' first.")
            sys.exit(1)

    print(f"Loading jobs from {filepath}...")
    jobs = load_scraped_jobs(str(filepath))
    if not jobs:
        print("No jobs found in file.")
        sys.exit(1)

    print(f"Preparing {len(jobs)} jobs for Claude...")
    slim_jobs = prepare_jobs(jobs)

    # Determine run dir
    run_dir = getattr(args, "_run_dir", None)
    if run_dir is None:
        if RUNS_DIR in filepath.resolve().parents:
            run_dir = filepath.resolve().parent
        else:
            run_dir = _create_run_dir()
        args._run_dir = run_dir

    # Save prepared.json
    from ranker.relevance import build_relevance

    outpath = Path(run_dir) / "prepared.json"
    data = {
        "prepared_at": datetime.now().isoformat(),
        "source_file": str(filepath),
        "total_jobs": len(slim_jobs),
        "relevance": build_relevance(slim_jobs, "prepared"),
        "jobs": slim_jobs,
    }
    outpath.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))

    # Token estimate (~4 chars per token for English/French mixed text)
    payload_chars = len(json.dumps(slim_jobs, default=str))
    token_est = payload_chars // 4

    # Summary
    print(f"\n{'='*60}")
    print(f"  PREPARED FOR CLAUDE")
    print(f"{'='*60}")
    print(f"  Jobs:           {len(slim_jobs)}")
    print(f"  Payload size:   {payload_chars:,} chars (~{token_est:,} tokens est.)")
    print(f"  Max output:     {8192} tokens (CLAUDE_MAX_TOKENS)")

    # Fields per job
    if slim_jobs:
        sample = slim_jobs[0]
        fields = list(sample.keys())
        print(f"  Fields per job: {', '.join(fields)}")
        has_rag = sum(1 for j in slim_jobs if j.get("resume_context"))
        print(f"  With RAG ctx:   {has_rag}/{len(slim_jobs)} jobs")

    # Top 5 preview
    print(f"\n  Top 5 preview:")
    print(f"    {'Title':<35} {'Company':<20} {'Stack':<8} {'Desc len':>8}")
    print(f"    {'─'*35} {'─'*20} {'─'*8} {'─'*8}")
    for j in slim_jobs[:5]:
        print(f"    {j.get('title', '?')[:35]:<35} "
              f"{j.get('company', '?')[:20]:<20} "
              f"{j.get('matched_stack', '-'):<8} "
              f"{len(j.get('description', '')):>8}")

    print(f"{'='*60}")
    print(f"\nSaved to {outpath}")
    print(f"\nInspect the file, then rank:")
    print(f"  python scripts/pipeline.py rank")

    return slim_jobs


# ─── Rank ────────────────────────────────────────────────────────────────────

def cmd_rank(args):
    """Rank jobs using Claude. Uses prepared.json if available, otherwise filtered/scraped."""
    from ranker.rank import load_scraped_jobs, rank_jobs, save_ranked

    if args.file:
        filepath = Path(args.file)
        is_prepared = "prepared" in filepath.name
    else:
        # Prefer prepared.json, then filtered, then scraped
        filepath = _find_latest_file("prepared_")
        is_prepared = filepath is not None
        if filepath:
            print(f"Found prepared file: {filepath.name}")
        else:
            filepath = _find_latest_file("filtered_top_")
            if filepath:
                print(f"Found top-bucket file: {filepath.name}")
            elif _find_latest_file("filtered_strong_"):
                filepath = _find_latest_file("filtered_strong_")
                print(f"Found strong-bucket file: {filepath.name}")
            else:
                filepath = _find_latest_file("scraped_")
        if not filepath:
            print("No prepared, filtered, or scraped files found. Run 'prepare', 'filter', or 'scrape' first.")
            sys.exit(1)

    print(f"Loading jobs from {filepath}...")
    jobs = load_scraped_jobs(str(filepath))
    if not jobs:
        print("No jobs found in file.")
        sys.exit(1)

    is_filtered = "filtered_" in filepath.name

    if is_prepared:
        print(f"Loaded {len(jobs)} pre-prepared jobs. Sending to Claude...")
    elif is_filtered:
        print(f"Loaded {len(jobs)} pre-filtered jobs. Preparing + sending to Claude...")
    else:
        print(f"Loaded {len(jobs)} jobs. Filtering + preparing + sending to Claude...")

    ranked = rank_jobs(jobs, target_role=args.role, skip_filter=(is_filtered or is_prepared), prepared=is_prepared)

    # Determine run dir
    run_dir = getattr(args, "_run_dir", None)
    if run_dir is None:
        if RUNS_DIR in filepath.resolve().parents:
            run_dir = filepath.resolve().parent
        else:
            run_dir = _create_run_dir()
        args._run_dir = run_dir

    outpath = save_ranked(ranked, str(OUTPUT_DIR), run_dir=str(run_dir))
    print(f"\nRanked results saved to {outpath}")

    # Print summary
    summary = ranked.get("search_summary", {})
    if summary:
        print(f"\n  Jobs analyzed: {summary.get('total_jobs_analyzed', '?')}")
        print(f"  Average fit:   {summary.get('average_fit_score', '?')}")
        print(f"  Top fit:       {summary.get('top_fit_score', '?')}")
        dist = summary.get("score_distribution", {})
        if dist:
            print(f"  Distribution:  {dist.get('excellent_80_plus', 0)} excellent, "
                  f"{dist.get('good_60_79', 0)} good, "
                  f"{dist.get('fair_40_59', 0)} fair, "
                  f"{dist.get('poor_below_40', 0)} poor")

    return ranked


# ─── Review (Human-in-the-Loop) ─────────────────────────────────────────────

PRIORITY_ORDER = ["apply_now", "strong_match", "worth_trying", "long_shot", "skip"]
PRIORITY_LABELS = {
    "apply_now": "APPLY NOW",
    "strong_match": "STRONG MATCH",
    "worth_trying": "WORTH TRYING",
    "long_shot": "LONG SHOT",
    "skip": "SKIP",
}


def _import_job_to_tracker(job: dict):
    """Import a ranked job into the opportunity tracker."""
    tracker_file = OUTPUT_DIR / "opportunities.json"
    if tracker_file.exists():
        data = json.loads(tracker_file.read_text())
    else:
        data = {"opportunities": [], "next_id": 1}

    # Check for duplicate by URL
    existing_urls = {o.get("url") for o in data["opportunities"]}
    if job.get("url") in existing_urls:
        print(f"    Already tracked (duplicate URL).")
        return

    opp = {
        "id": data["next_id"],
        "company": job.get("company", ""),
        "role": job.get("title", ""),
        "location": job.get("location", ""),
        "remote": "",
        "contract": "",
        "source": job.get("source", "scraper"),
        "url": job.get("url", ""),
        "salary": "",
        "status": "New",
        "applied_date": None,
        "follow_up_date": None,
        "notes": f"Score: {job.get('scores', {}).get('overall', '?')}/100 | "
                 f"Priority: {job.get('priority', '?')} | "
                 f"Skills: {', '.join(job.get('matching_skills', [])[:5])}",
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "history": [],
    }
    data["opportunities"].append(opp)
    data["next_id"] += 1

    tracker_file.parent.mkdir(parents=True, exist_ok=True)
    tracker_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"    Imported as #{opp['id']} in opportunity tracker.")


def cmd_review(args):
    """Interactive review of ranked jobs."""
    if args.file:
        filepath = Path(args.file)
    else:
        filepath = _find_latest_file("ranked_")
        if not filepath:
            print("No ranked files found. Run 'rank' first.")
            sys.exit(1)

    print(f"Loading ranked jobs from {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        ranked = json.load(f)

    jobs = ranked.get("ranked_jobs", [])
    if not jobs:
        print("No ranked jobs found in file.")
        return

    # Group by priority
    by_priority = {}
    for job in jobs:
        p = job.get("priority", "skip")
        by_priority.setdefault(p, []).append(job)

    approved = 0
    skipped = 0

    print(f"\n{'='*60}")
    print(f"  RANKED JOBS REVIEW — {len(jobs)} jobs")
    print(f"{'='*60}")

    for priority in PRIORITY_ORDER:
        group = by_priority.get(priority, [])
        if not group:
            continue

        label = PRIORITY_LABELS.get(priority, priority.upper())
        print(f"\n{'─'*60}")
        print(f"  {label} ({len(group)} jobs)")
        print(f"{'─'*60}")

        for job in group:
            scores = job.get("scores", {})
            print(f"\n  [{scores.get('overall', '?')}/100] {job.get('title', '?')}")
            print(f"  Company:  {job.get('company', '?')}")
            print(f"  Location: {job.get('location', '?')}")
            print(f"  Scores:   Skills={scores.get('skills_match', '?')} "
                  f"Exp={scores.get('experience_fit', '?')} "
                  f"Loc={scores.get('location_fit', '?')} "
                  f"Growth={scores.get('growth_potential', '?')}")

            matching = job.get("matching_skills", [])
            missing = job.get("missing_skills", [])
            if matching:
                print(f"  Match:    {', '.join(matching[:6])}")
            if missing:
                print(f"  Missing:  {', '.join(missing[:4])}")

            # Prompt user
            while True:
                choice = input("  [a]pprove | [s]kip | [v]iew full | [c]heck url | [q]uit: ").strip().lower()
                if choice == "a":
                    _import_job_to_tracker(job)
                    approved += 1
                    break
                elif choice == "s":
                    skipped += 1
                    break
                elif choice == "v":
                    print(f"\n  URL:     {job.get('url', 'N/A')}")
                    print(f"  Source:  {job.get('source', '?')}")
                    tweaks = job.get("resume_tweaks", [])
                    if tweaks:
                        print(f"  Resume tweaks:")
                        for t in tweaks:
                            print(f"    - {t}")
                    print()
                elif choice == "c":
                    url = job.get("url", "")
                    if not url:
                        print("  No URL available.")
                        continue
                    print(f"  Checking {url}...")
                    from scraper.url_validator import check_single_url
                    result = check_single_url(url, job.get("source", ""))
                    status = result["url_status"]
                    if status == "live":
                        print(f"  LIVE (HTTP {result['url_status_code']})")
                    elif status in ("closed", "not_found"):
                        print(f"  CLOSED ({status}, HTTP {result['url_status_code']})")
                    else:
                        print(f"  Could not verify ({status}, HTTP {result['url_status_code']})")
                elif choice == "q":
                    print(f"\nReview ended. Approved: {approved}, Skipped: {skipped}")
                    return
                else:
                    print("  Invalid choice. Use a/s/v/c/q.")

    print(f"\nReview complete. Approved: {approved}, Skipped: {skipped}")


# ─── Run (Full Pipeline) ────────────────────────────────────────────────────

def cmd_run(args):
    """Run full pipeline: scrape → enrich → filter → validate → prepare → rank → review."""
    skip_validate = getattr(args, "skip_validate", False)
    total_steps = 6 if skip_validate else 7
    step = 0

    print("=" * 60)
    if skip_validate:
        print("  FULL PIPELINE: Scrape → Enrich → Filter → Prepare → Rank → Review")
    else:
        print("  FULL PIPELINE: Scrape → Enrich → Filter → Validate → Prepare → Rank → Review")
    print("=" * 60)

    # Create ONE run dir for the entire pipeline
    run_dir = _create_run_dir()
    args._run_dir = run_dir
    logger.info(f"Run directory: {run_dir}")

    # Step 1: Scrape
    step += 1
    print(f"\n[{step}/{total_steps}] SCRAPING...")
    jobs = cmd_scrape(args)
    if not jobs:
        print("No jobs scraped. Pipeline stopped.")
        return

    # Step 2: Enrich Indeed descriptions
    step += 1
    print(f"\n[{step}/{total_steps}] ENRICHING...")
    args.file = None
    args.max_enrich = getattr(args, "max_enrich", 50)
    cmd_enrich(args)

    # Step 3: Filter
    step += 1
    print(f"\n[{step}/{total_steps}] FILTERING...")
    args.file = None
    args.threshold = getattr(args, "threshold", None)
    cmd_filter(args)

    # Step 4: Validate (optional)
    if not skip_validate:
        step += 1
        print(f"\n[{step}/{total_steps}] VALIDATING URLs...")
        args.file = None
        cmd_validate(args)

    # Step N: Prepare
    step += 1
    print(f"\n[{step}/{total_steps}] PREPARING...")
    args.file = None
    cmd_prepare(args)

    # Step N+1: Rank
    step += 1
    print(f"\n[{step}/{total_steps}] RANKING...")
    args.file = None
    args.role = getattr(args, "role", None)
    ranked = cmd_rank(args)

    # Step N+2: Review
    step += 1
    print(f"\n[{step}/{total_steps}] REVIEW...")
    args.file = None
    cmd_review(args)


# ─── Manual ──────────────────────────────────────────────────────────────────

def cmd_manual(args):
    """Add a job manually via the opportunity tracker."""
    import subprocess
    tracker_script = ROOT / "scripts" / "opportunity_tracker.py"
    subprocess.run([sys.executable, str(tracker_script), "add"])


# ─── Status ──────────────────────────────────────────────────────────────────

def cmd_status(args):
    """Show pipeline statistics across all stages."""
    print(f"\n{'='*50}")
    print(f"  PIPELINE STATUS")
    print(f"{'='*50}")

    # Scraped files (run dirs + legacy flat files)
    scraped_files = sorted(RUNS_DIR.glob("*/scraped.json"), reverse=True) if RUNS_DIR.is_dir() else []
    scraped_files += sorted(OUTPUT_DIR.glob("scraped_*.json"), reverse=True)
    total_scraped = 0
    for f in scraped_files[:5]:
        try:
            data = json.loads(f.read_text())
            count = data.get("total_jobs", len(data.get("jobs", [])))
            total_scraped += count
        except (json.JSONDecodeError, KeyError):
            pass

    print(f"\n  Scraped files: {len(scraped_files)}")
    if scraped_files:
        print(f"  Latest: {scraped_files[0]}")
        print(f"  Total jobs (last 5 files): {total_scraped}")

    # Ranked files (run dirs + legacy flat files)
    ranked_files = sorted(RUNS_DIR.glob("*/ranked.json"), reverse=True) if RUNS_DIR.is_dir() else []
    ranked_files += sorted(OUTPUT_DIR.glob("ranked_*.json"), reverse=True)
    total_ranked = 0
    for f in ranked_files[:5]:
        try:
            data = json.loads(f.read_text())
            total_ranked += len(data.get("ranked_jobs", []))
        except (json.JSONDecodeError, KeyError):
            pass

    print(f"\n  Ranked files: {len(ranked_files)}")
    if ranked_files:
        print(f"  Latest: {ranked_files[0]}")
        print(f"  Total ranked (last 5 files): {total_ranked}")

    # Tracker
    tracker_file = OUTPUT_DIR / "opportunities.json"
    if tracker_file.exists():
        try:
            data = json.loads(tracker_file.read_text())
            opps = data.get("opportunities", [])
            by_status = {}
            for o in opps:
                by_status[o["status"]] = by_status.get(o["status"], 0) + 1

            print(f"\n  Tracked opportunities: {len(opps)}")
            for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
                print(f"    {status}: {count}")
        except (json.JSONDecodeError, KeyError):
            print("\n  Tracker: error reading file")
    else:
        print("\n  Tracker: no data yet")

    # Contacts
    contacts_file = OUTPUT_DIR / "contacts.json"
    if contacts_file.exists():
        try:
            data = json.loads(contacts_file.read_text())
            contacts = data.get("contacts", [])
            print(f"\n  Tracked contacts: {len(contacts)}")
        except (json.JSONDecodeError, KeyError):
            pass

    print(f"\n{'='*50}")


# ─── Sync ────────────────────────────────────────────────────────────────────

RCLONE_REMOTE = "gdrive"
RCLONE_DEST = "job-search/output"

def cmd_sync(args):
    """Sync output/latest + persistent files to Google Drive via rclone."""
    import shutil
    import subprocess

    if not shutil.which("rclone"):
        logger.error("rclone not installed. Run: curl https://rclone.org/install.sh | bash")
        sys.exit(1)

    remote = f"{RCLONE_REMOTE}:{RCLONE_DEST}"

    # Resolve what to sync
    targets = []

    # Latest run
    latest = OUTPUT_DIR / "latest"
    if latest.exists():
        run_name = latest.resolve().name  # e.g. 2026-03-08-23-32-06
        targets.append((str(latest) + "/", f"{remote}/runs/{run_name}/"))
        targets.append((str(latest) + "/", f"{remote}/latest/"))

    # Persistent files
    for name in ("opportunities.json", "contacts.json"):
        path = OUTPUT_DIR / name
        if path.exists():
            targets.append((str(path), f"{remote}/{name}"))

    if not targets:
        logger.warning("Nothing to sync — no output/latest or persistent files found.")
        return

    print(f"\n{'='*50}")
    print(f"  SYNC TO GOOGLE DRIVE")
    print(f"{'='*50}")

    for src, dst in targets:
        # Use 'copy' for files, 'copy' for dirs
        is_dir = src.endswith("/")
        label = Path(src.rstrip("/")).name
        print(f"\n  [{label}] → {dst}")

        cmd = ["rclone", "copy", src, dst, "--progress"]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            logger.error(f"Failed to sync {label}")
        else:
            print(f"  [{label}] done.")

    print(f"\n{'='*50}")
    print(f"  Sync complete.")
    print(f"{'='*50}\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Job search pipeline: scrape → rank → review → track",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", help="Pipeline command")

    # scrape
    p_scrape = sub.add_parser("scrape", help="Run job scrapers")
    p_scrape.add_argument("--sources", nargs="+", choices=list(AVAILABLE_SCRAPERS),
                          help="Which scrapers to run (default: all)")
    p_scrape.add_argument("--keywords", nargs="+", help="Override default keywords")
    p_scrape.add_argument("--regions", nargs="+", help="Filter by regions")
    p_scrape.add_argument("--max-pages", type=int, default=3, help="Max pages per source")

    # index
    p_index = sub.add_parser("index", help="Index resumes into ChromaDB for semantic filtering")
    p_index.add_argument("--force", action="store_true", help="Force reindex even if unchanged")

    # enrich
    p_enrich = sub.add_parser("enrich", help="Enrich Indeed jobs with full descriptions")
    p_enrich.add_argument("--file", help="Path to scraped JSON (default: latest)")
    p_enrich.add_argument("--max-enrich", type=int, default=50,
                          help="Max Indeed jobs to enrich (default: 50)")

    # filter
    p_filter = sub.add_parser("filter", help="Semantic filter only (no Claude API call)")
    p_filter.add_argument("--file", help="Path to scraped JSON (default: latest)")
    p_filter.add_argument("--threshold", type=float, help="Override similarity threshold (default: 0.65)")

    # validate
    p_validate = sub.add_parser("validate", help="Check job URLs for closed/expired postings")
    p_validate.add_argument("--file", help="Path to filtered/scraped JSON (default: latest)")
    p_validate.add_argument("--max-validate", type=int, default=200,
                            help="Max URLs to check (default: 200)")
    p_validate.add_argument("--recheck", action="store_true",
                            help="Re-check jobs that already have url_status")

    # prepare
    p_prepare = sub.add_parser("prepare", help="Slim jobs for Claude — inspect before ranking (no API call)")
    p_prepare.add_argument("--file", help="Path to filtered JSON (default: latest)")

    # rank
    p_rank = sub.add_parser("rank", help="Rank jobs with Claude (uses prepared.json if available)")
    p_rank.add_argument("--file", help="Path to prepared/filtered JSON (default: latest)")
    p_rank.add_argument("--role", help="Target role focus for ranking")

    # review
    p_review = sub.add_parser("review", help="Interactive review of ranked jobs")
    p_review.add_argument("--file", help="Path to ranked JSON (default: latest)")

    # run (full pipeline)
    p_run = sub.add_parser("run", help="Full pipeline: scrape → rank → review")
    p_run.add_argument("--sources", nargs="+", choices=list(AVAILABLE_SCRAPERS),
                       help="Which scrapers to run (default: all)")
    p_run.add_argument("--keywords", nargs="+", help="Override default keywords")
    p_run.add_argument("--regions", nargs="+", help="Filter by regions")
    p_run.add_argument("--max-pages", type=int, default=3, help="Max pages per source")
    p_run.add_argument("--role", help="Target role focus for ranking")
    p_run.add_argument("--skip-validate", action="store_true",
                       help="Skip URL validation stage")

    # manual
    sub.add_parser("manual", help="Add a job manually to tracker")

    # status
    sub.add_parser("status", help="Show pipeline statistics")

    # sync
    sub.add_parser("sync", help="Sync output/latest + persistent files to Google Drive")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "scrape": cmd_scrape,
        "index": cmd_index,
        "enrich": cmd_enrich,
        "filter": cmd_filter,
        "validate": cmd_validate,
        "prepare": cmd_prepare,
        "rank": cmd_rank,
        "review": cmd_review,
        "run": cmd_run,
        "manual": cmd_manual,
        "status": cmd_status,
        "sync": cmd_sync,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
