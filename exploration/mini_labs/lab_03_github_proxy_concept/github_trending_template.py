import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


# CONFIG - CHANGE ONLY THIS SECTION
GITHUB_TOPICS_BASE_URL = "https://github.com/topics"
CATEGORY_TOPICS = {
    "system": ["operating-systems", "linux", "windows", "macos"],
    "networking": ["networking"],
    "security": ["security"],
}
TOTAL_LIMIT = 10
PAGES_PER_TOPIC = 2
TIMEOUT = 25
OUTPUT_FILENAME = "github_all_time_top10.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# Polite delay between requests (seconds)
REQUEST_DELAY = 2


def bytes_to_megabytes(size_bytes: int) -> float:
    return round(size_bytes / (1024 * 1024), 4)


def parse_star_count(raw_text: str) -> int:
    text = re.sub(r"\s+", "", raw_text.lower().replace(",", ""))
    match = re.search(r"(\d+(?:\.\d+)?)([kmb]?)", text)
    if not match:
        return 0

    number = float(match.group(1))
    suffix = match.group(2)
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    return int(number * multiplier[suffix])


def parse_topic_page(html: str, category: str, topic_slug: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: Dict[str, Dict[str, object]] = {}

    for card in soup.select("article"):
        repo_href = ""
        for anchor in card.select("h3 a[href]"):
            href = anchor.get("href", "").strip()
            if href.startswith("/") and href.count("/") >= 2:
                repo_href = href
                break

        if not repo_href:
            continue

        repo_name = repo_href.strip("/")

        stars_raw = "0"
        match = re.search(r"Star\s+(\d+(?:\.\d+)?[kmb]?)", card.get_text(" ", strip=True), re.IGNORECASE)
        if match:
            stars_raw = match.group(1)
        stars = parse_star_count(stars_raw)

        desc_tag = card.select_one("p")
        description = desc_tag.get_text(" ", strip=True) if desc_tag else ""

        existing = rows.get(repo_name)
        if existing is None or stars > int(existing["stars"]):
            rows[repo_name] = {
                "category": category,
                "topic": topic_slug,
                "repo": repo_name,
                "url": f"https://github.com/{repo_name}",
                "stars": stars,
                "stars_raw": stars_raw,
                "description": description,
            }

    results = list(rows.values())
    results.sort(key=lambda row: int(row["stars"]), reverse=True)
    return results


def fetch_topic_candidates(
    session: requests.Session,
    category: str,
    topic_slugs: List[str],
    stats: Dict[str, int],
) -> List[Dict[str, object]]:
    combined: Dict[str, Dict[str, object]] = {}

    for slug in topic_slugs:
        for page in range(1, PAGES_PER_TOPIC + 1):
            url = f"{GITHUB_TOPICS_BASE_URL}/{slug}?page={page}"

            response = session.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()

            resp_bytes = len(response.content)
            stats["requests"] += 1
            stats["response_bytes"] += resp_bytes

            for row in parse_topic_page(response.text, category, slug):
                repo = str(row["repo"])
                best = combined.get(repo)
                if best is None or int(row["stars"]) > int(best["stars"]):
                    combined[repo] = row

            time.sleep(REQUEST_DELAY)

    ranked = list(combined.values())
    ranked.sort(key=lambda row: int(row["stars"]), reverse=True)
    return ranked


def select_top(ranked_by_category: Dict[str, List[Dict[str, object]]]) -> List[Dict[str, object]]:
    categories = list(ranked_by_category.keys())
    per_category = TOTAL_LIMIT // len(categories)

    selected: List[Dict[str, object]] = []
    used = set()

    for category in categories:
        count = 0
        for row in ranked_by_category[category]:
            repo = str(row["repo"])
            if repo in used:
                continue
            selected.append(row)
            used.add(repo)
            count += 1
            if count == per_category:
                break

    if len(selected) < TOTAL_LIMIT:
        overflow: List[Dict[str, object]] = []
        for category in categories:
            overflow.extend(ranked_by_category[category])
        overflow.sort(key=lambda row: int(row["stars"]), reverse=True)

        for row in overflow:
            repo = str(row["repo"])
            if repo in used:
                continue
            selected.append(row)
            used.add(repo)
            if len(selected) == TOTAL_LIMIT:
                break

    selected.sort(key=lambda row: int(row["stars"]), reverse=True)
    return selected[:TOTAL_LIMIT]


def main() -> None:
    session = requests.Session()
    stats = {"requests": 0, "response_bytes": 0}
    run_started = time.monotonic()

    ranked_by_category: Dict[str, List[Dict[str, object]]] = {}
    for category, topic_slugs in CATEGORY_TOPICS.items():
        ranked_by_category[category] = fetch_topic_candidates(
            session=session,
            category=category,
            topic_slugs=topic_slugs,
            stats=stats,
        )

    top = select_top(ranked_by_category)
    run_duration = max(time.monotonic() - run_started, 0.001)

    output = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "signal": "GitHub topic pages (top-starred repos as all-time community popularity proxy)",
        "total_limit": TOTAL_LIMIT,
        "category_topics": CATEGORY_TOPICS,
        "traffic": {
            "requests": stats["requests"],
            "response_megabytes": bytes_to_megabytes(stats["response_bytes"]),
            "run_duration_seconds": round(run_duration, 3),
        },
        "results": top,
    }

    output_path = Path(__file__).with_name(OUTPUT_FILENAME)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    print(f"Saved {len(top)} repos to: {output_path}")
    print(
        f"Traffic: {stats['requests']} requests, "
        f"{bytes_to_megabytes(stats['response_bytes'])} MB, "
        f"{round(run_duration, 1)}s"
    )
    for row in top:
        print(f"  [{row['category']}] {row['repo']} ({row['stars_raw']})")


if __name__ == "__main__":
    main()
