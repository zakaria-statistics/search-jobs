import json
import os
from datetime import datetime
from pathlib import Path

from .models import Job


def save_jobs(jobs: list[Job], output_dir: str = None) -> str:
    """Save jobs to a daily JSON file. Returns the file path."""
    if output_dir is None:
        output_dir = str(Path(__file__).parent.parent / "output")
    os.makedirs(output_dir, exist_ok=True)

    now_stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filepath = os.path.join(output_dir, f"scraped_{now_stamp}.json")

    # Dedup by URL
    seen = set()
    unique = []
    for job in jobs:
        if job.url not in seen:
            seen.add(job.url)
            unique.append(job)

    # If file already exists, merge with existing jobs
    existing_jobs = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_jobs = existing_data.get("jobs", [])
            for ej in existing_jobs:
                if ej.get("url") not in seen:
                    seen.add(ej["url"])
                    unique.append(Job(**{k: ej.get(k, "") for k in Job.__dataclass_fields__}))
        except (json.JSONDecodeError, KeyError):
            pass

    data = {
        "scraped_at": datetime.now().isoformat(),
        "total_jobs": len(unique),
        "jobs": [job.to_dict() if isinstance(job, Job) else job for job in unique],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def print_summary(jobs: list[Job]):
    """Print a summary of scraped jobs."""
    if not jobs:
        print("No jobs found.")
        return

    # By source
    sources: dict[str, int] = {}
    for job in jobs:
        sources[job.source] = sources.get(job.source, 0) + 1

    # By region
    regions: dict[str, int] = {}
    for job in jobs:
        regions[job.region] = regions.get(job.region, 0) + 1

    print(f"\n{'='*50}")
    print(f"Total jobs scraped: {len(jobs)}")
    print(f"\nBy source:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")
    print(f"\nBy region:")
    for reg, count in sorted(regions.items()):
        print(f"  {reg}: {count}")
    print(f"{'='*50}\n")
