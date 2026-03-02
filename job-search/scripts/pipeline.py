#!/usr/bin/env python3
"""
pipeline.py — Unified job search pipeline: scrape → rank → review → track.

Usage:
    python scripts/pipeline.py scrape          # Run all scrapers
    python scripts/pipeline.py scrape --sources indeed remoteok
    python scripts/pipeline.py rank            # Rank latest scraped file with Claude
    python scripts/pipeline.py rank --file output/scraped_2026-03-02.json
    python scripts/pipeline.py review          # Interactive: show ranked jobs, approve/skip
    python scripts/pipeline.py run             # Full pipeline: scrape → rank → review
    python scripts/pipeline.py manual          # Add a job manually (delegates to tracker)
    python scripts/pipeline.py status          # Show pipeline stats
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

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


# ─── Scrape ──────────────────────────────────────────────────────────────────

AVAILABLE_SCRAPERS = {
    "indeed": "scraper.IndeedScraper",
    "remoteok": "scraper.RemoteOKScraper",
    "arbeitnow": "scraper.ArbeitnowScraper",
    "rekrute": "scraper.RekruteScraper",
    "wttj": "scraper.WTTJScraper",
}


def cmd_scrape(args):
    """Run scrapers and save results."""
    from scraper import IndeedScraper, RemoteOKScraper, ArbeitnowScraper, RekruteScraper, WTTJScraper
    from scraper.config import KEYWORDS
    from scraper.storage import save_jobs, print_summary

    scraper_map = {
        "indeed": IndeedScraper,
        "remoteok": RemoteOKScraper,
        "arbeitnow": ArbeitnowScraper,
        "rekrute": RekruteScraper,
        "wttj": WTTJScraper,
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
        filepath = save_jobs(all_jobs, str(OUTPUT_DIR))
        print_summary(all_jobs)
        print(f"Saved {len(all_jobs)} jobs to {filepath}")
    else:
        print("No jobs found across any source.")

    return all_jobs


# ─── Rank ────────────────────────────────────────────────────────────────────

def _find_latest_file(prefix: str) -> Path | None:
    """Find the most recent file matching prefix in output dir."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(OUTPUT_DIR.glob(f"{prefix}*.json"), reverse=True)
    return files[0] if files else None


def cmd_rank(args):
    """Rank scraped jobs using Claude."""
    from ranker.rank import load_scraped_jobs, rank_jobs, save_ranked

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

    print(f"Loaded {len(jobs)} jobs. Sending to Claude for ranking...")
    ranked = rank_jobs(jobs, target_role=args.role)

    outpath = save_ranked(ranked, str(OUTPUT_DIR))
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
                choice = input("  [a]pprove | [s]kip | [v]iew full | [q]uit: ").strip().lower()
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
                elif choice == "q":
                    print(f"\nReview ended. Approved: {approved}, Skipped: {skipped}")
                    return
                else:
                    print("  Invalid choice. Use a/s/v/q.")

    print(f"\nReview complete. Approved: {approved}, Skipped: {skipped}")


# ─── Run (Full Pipeline) ────────────────────────────────────────────────────

def cmd_run(args):
    """Run full pipeline: scrape → rank → review."""
    print("=" * 60)
    print("  FULL PIPELINE: Scrape → Rank → Review")
    print("=" * 60)

    # Step 1: Scrape
    print("\n[1/3] SCRAPING...")
    jobs = cmd_scrape(args)
    if not jobs:
        print("No jobs scraped. Pipeline stopped.")
        return

    # Step 2: Rank
    print("\n[2/3] RANKING...")
    args.file = None  # Use latest scraped file
    args.role = getattr(args, "role", None)
    ranked = cmd_rank(args)

    # Step 3: Review
    print("\n[3/3] REVIEW...")
    args.file = None  # Use latest ranked file
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

    # Scraped files
    scraped_files = sorted(OUTPUT_DIR.glob("scraped_*.json"), reverse=True)
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
        print(f"  Latest: {scraped_files[0].name}")
        print(f"  Total jobs (last 5 files): {total_scraped}")

    # Ranked files
    ranked_files = sorted(OUTPUT_DIR.glob("ranked_*.json"), reverse=True)
    total_ranked = 0
    for f in ranked_files[:5]:
        try:
            data = json.loads(f.read_text())
            total_ranked += len(data.get("ranked_jobs", []))
        except (json.JSONDecodeError, KeyError):
            pass

    print(f"\n  Ranked files: {len(ranked_files)}")
    if ranked_files:
        print(f"  Latest: {ranked_files[0].name}")
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

    # rank
    p_rank = sub.add_parser("rank", help="Rank scraped jobs with Claude")
    p_rank.add_argument("--file", help="Path to scraped JSON (default: latest)")
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

    # manual
    sub.add_parser("manual", help="Add a job manually to tracker")

    # status
    sub.add_parser("status", help="Show pipeline statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "scrape": cmd_scrape,
        "rank": cmd_rank,
        "review": cmd_review,
        "run": cmd_run,
        "manual": cmd_manual,
        "status": cmd_status,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
