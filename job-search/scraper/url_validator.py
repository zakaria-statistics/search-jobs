"""
url_validator.py — Check whether scraped job URLs are still live.

Detects closed/expired job postings by HTTP status, redirects, and
page-content patterns. Used as a pipeline stage between filter and prepare.
"""

import logging
import random
import re
import time
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# ─── Per-source closed-page patterns (regex, case-insensitive) ─────────────

SOURCE_DETECTORS = {
    "indeed": {
        "fetcher": "stealthy",
        "patterns": [
            r"this job has expired",
            r"cette offre.*n'est plus disponible",
        ],
    },
    "wttj": {
        "fetcher": "requests",
        "patterns": [
            r"cette offre n'est plus disponible",
            r"offre expir[ée]e",
        ],
    },
    "remoteok": {
        "fetcher": "requests",
        "patterns": [
            r"this job is no longer available",
            r"position has been filled",
        ],
    },
    "arbeitnow": {
        "fetcher": "requests",
        "patterns": [
            r"job not found",
            r"position is no longer available",
        ],
    },
    "rekrute": {
        "fetcher": "stealthy",
        "patterns": [
            r"offre expir[ée]e",
            r"offre cl[oô]tur[ée]e",
        ],
    },
}

# Redirect signals: if the final URL contains these and the original didn't
_REDIRECT_CLOSED_SIGNALS = ["/jobs?", "/search?", "/expired", "/404"]

# Requests session (reused for non-stealthy fetches)
_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        })
    return _session


def _fetch_with_requests(url: str, timeout: int = 15) -> tuple[int, str, str]:
    """Fetch URL with requests. Returns (status_code, final_url, text[:5000])."""
    try:
        resp = _get_session().get(url, timeout=timeout, allow_redirects=True)
        return resp.status_code, resp.url, resp.text[:5000]
    except requests.RequestException as e:
        logger.debug(f"Request failed for {url}: {e}")
        return 0, url, ""


def _fetch_with_stealthy(url: str) -> tuple[int, str, str]:
    """Fetch URL with scrapling StealthyFetcher. Returns (status_code, final_url, text[:5000])."""
    try:
        from scrapling import StealthyFetcher
        fetcher = StealthyFetcher()
        page = fetcher.fetch(url, headless=True)
        status = page.status if hasattr(page, "status") else 200
        final_url = page.url if hasattr(page, "url") else url
        text = page.get_all_text() if hasattr(page, "get_all_text") else str(page.text)[:5000]
        return status, final_url, text[:5000]
    except Exception as e:
        logger.debug(f"StealthyFetcher failed for {url}: {e}")
        return 0, url, ""


def _detect_status(http_status: int, original_url: str, final_url: str,
                   page_text: str, patterns: list[str]) -> str:
    """Determine URL status from HTTP response data.

    Returns one of: 'live', 'closed', 'not_found', 'error'.
    """
    # 1. HTTP status codes
    if http_status == 404:
        return "not_found"
    if http_status == 410:
        return "closed"
    if http_status >= 400:
        return "error"
    if http_status == 0:
        return "error"

    # 2. Redirect check
    original_lower = original_url.lower()
    final_lower = final_url.lower()
    if original_lower != final_lower:
        for signal in _REDIRECT_CLOSED_SIGNALS:
            if signal in final_lower and signal not in original_lower:
                return "closed"

    # 3. Page content pattern matching
    text_lower = page_text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return "closed"

    # 4. No match → assumed live
    return "live"


def check_single_url(url: str, source: str = "") -> dict:
    """Check a single URL's liveness.

    Returns dict with keys: url_status, url_status_code, url_checked_at.
    """
    detector = SOURCE_DETECTORS.get(source, {"fetcher": "requests", "patterns": []})
    patterns = detector["patterns"]

    if detector["fetcher"] == "stealthy":
        status_code, final_url, text = _fetch_with_stealthy(url)
    else:
        status_code, final_url, text = _fetch_with_requests(url)

    url_status = _detect_status(status_code, url, final_url, text, patterns)

    return {
        "url_status": url_status,
        "url_status_code": status_code,
        "url_checked_at": datetime.now().isoformat(),
    }


def validate_jobs(jobs: list[dict], delay_min: float = 3, delay_max: float = 6,
                  max_jobs: int = 200, recheck: bool = False) -> list[dict]:
    """Batch-validate job URLs. Modifies jobs in-place, adding url_status fields.

    Args:
        jobs: List of job dicts (must have 'url' and 'source' keys).
        delay_min/delay_max: Random delay range between requests (seconds).
        max_jobs: Max number of jobs to check (0 = all).
        recheck: If True, re-check jobs that already have url_status.

    Returns:
        The same list of jobs (modified in-place).
    """
    to_check = []
    for j in jobs:
        if not recheck and j.get("url_status"):
            continue
        if j.get("url"):
            to_check.append(j)

    if max_jobs > 0:
        to_check = to_check[:max_jobs]

    if not to_check:
        logger.info("No jobs to validate.")
        return jobs

    logger.info(f"Validating {len(to_check)} URLs...")

    # Group by source for smarter rate limiting
    by_source = {}
    for j in to_check:
        src = j.get("source", "unknown")
        by_source.setdefault(src, []).append(j)

    checked = 0
    for source, source_jobs in by_source.items():
        logger.info(f"  Checking {len(source_jobs)} {source} URLs...")
        for i, job in enumerate(source_jobs):
            result = check_single_url(job["url"], source)
            job.update(result)
            checked += 1

            status_icon = {
                "live": "+", "closed": "x", "not_found": "!", "error": "?"
            }.get(result["url_status"], "?")
            logger.info(
                f"    [{status_icon}] {checked}/{len(to_check)} "
                f"{result['url_status']:>9} ({result['url_status_code']}) "
                f"{job.get('title', '?')[:40]}"
            )

            # Delay between requests (skip after last in group)
            if i < len(source_jobs) - 1:
                time.sleep(random.uniform(delay_min, delay_max))

    return jobs


def drop_closed(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split jobs into (live, closed) based on url_status.

    Jobs without url_status are considered live (unchecked).
    """
    live = []
    closed = []
    for j in jobs:
        status = j.get("url_status", "live")
        if status in ("closed", "not_found"):
            closed.append(j)
        else:
            live.append(j)
    return live, closed
