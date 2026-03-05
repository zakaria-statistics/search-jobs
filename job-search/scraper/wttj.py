import logging
from datetime import datetime

import requests

from .base import BaseScraper
from .config import WTTJ_MAX_PAGES, WTTJ_DELAY_MIN, WTTJ_DELAY_MAX, match_job
from .models import Job

logger = logging.getLogger(__name__)

# WTTJ Algolia configuration (public, embedded in their frontend)
_ALGOLIA_APP_ID = "CSEKHVMS53"
_ALGOLIA_API_KEY = "4bd8f6215d0cc52b26430765769e65a0"
_ALGOLIA_INDEX = "wttj_jobs_production_fr"
_ALGOLIA_URL = f"https://{_ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/{_ALGOLIA_INDEX}/query"
_ALGOLIA_HEADERS = {
    "x-algolia-application-id": _ALGOLIA_APP_ID,
    "x-algolia-api-key": _ALGOLIA_API_KEY,
    "content-type": "application/json",
    "referer": "https://www.welcometothejungle.com/",
    "origin": "https://www.welcometothejungle.com",
}

_HITS_PER_PAGE = 20


class WTTJScraper(BaseScraper):
    """Scrape Welcome to the Jungle (WTTJ) job listings via Algolia API."""

    name = "wttj"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        jobs = []
        pages = min(max_pages, WTTJ_MAX_PAGES)
        now = datetime.now().isoformat()

        for keyword in keywords:
            for page in range(pages):
                logger.info(f"WTTJ: '{keyword}' page {page + 1}")

                try:
                    resp = requests.post(
                        _ALGOLIA_URL,
                        headers=_ALGOLIA_HEADERS,
                        json={
                            "query": keyword,
                            "hitsPerPage": _HITS_PER_PAGE,
                            "page": page,
                        },
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.error(f"WTTJ Algolia error ('{keyword}', page {page + 1}): {e}")
                    break

                hits = data.get("hits", [])
                if not hits:
                    break

                for hit in hits:
                    title = hit.get("name", "")
                    if not title:
                        continue

                    org = hit.get("organization", {})
                    company = org.get("name", "")
                    description = hit.get("profile") or hit.get("description") or ""
                    tags = " ".join(
                        s.get("name", "") for s in hit.get("sectors", [])
                    )

                    matched = match_job(title, tags, keywords,
                                        description=description, lenient=True)
                    if not matched:
                        continue

                    # Build URL
                    org_slug = org.get("slug", "")
                    job_slug = hit.get("slug", "")
                    if org_slug and job_slug:
                        job_url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{job_slug}"
                    else:
                        ref = hit.get("reference", "")
                        job_url = f"https://www.welcometothejungle.com/fr/jobs/{ref}" if ref else ""

                    # Location
                    office = hit.get("office") or {}
                    if isinstance(office, dict):
                        city = office.get("city", "")
                        country = office.get("country_code", "")
                        location = f"{city}, {country}".strip(", ") if city else country
                    else:
                        location = ""

                    remote = hit.get("remote", "")
                    if remote and remote != "unknown":
                        location = f"{location} ({remote})".strip() if location else remote

                    # Determine region
                    region = _detect_region(location)

                    # Salary info
                    salary_parts = []
                    sal_min = hit.get("salary_minimum")
                    sal_max = hit.get("salary_maximum")
                    sal_cur = hit.get("salary_currency", "")
                    if sal_min or sal_max:
                        salary_parts.append(
                            f"{int(sal_min or 0)}-{int(sal_max or 0)} {sal_cur}".strip()
                        )

                    contract = hit.get("contract_type", "")
                    desc_parts = [description[:500]] if description else []
                    if contract:
                        desc_parts.append(f"Contract: {contract}")
                    if salary_parts:
                        desc_parts.append(f"Salary: {salary_parts[0]}")

                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        source="wttj",
                        date_posted=hit.get("published_at", ""),
                        description=" | ".join(desc_parts),
                        keyword=matched,
                        region=region,
                        scraped_at=now,
                    ))

                if len(hits) < _HITS_PER_PAGE:
                    break

                self.delay(WTTJ_DELAY_MIN, WTTJ_DELAY_MAX)

        logger.info(f"WTTJ: found {len(jobs)} jobs total")
        return self.dedup(jobs)


def _detect_region(location: str) -> str:
    loc = location.lower()
    if any(c in loc for c in ("maroc", "morocco", "casablanca", "rabat")):
        return "morocco"
    if any(c in loc for c in ("germany", "berlin", "munich", "de", "deutschland")):
        return "germany"
    if any(c in loc for c in ("netherlands", "amsterdam", "nl")):
        return "netherlands"
    if any(c in loc for c in ("belgium", "brussels", "be", "bruxelles")):
        return "belgium"
    if any(c in loc for c in ("uk", "gb", "london", "united kingdom")):
        return "uk"
    if any(c in loc for c in ("ch", "switzerland", "zurich", "geneva")):
        return "switzerland"
    if "remote" in loc:
        return "remote"
    return "france"
