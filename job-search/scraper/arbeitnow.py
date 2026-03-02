import logging
from datetime import datetime

import requests

from .base import BaseScraper
from .config import ARBEITNOW_API_URL, ARBEITNOW_MAX_PAGES, match_job
from .models import Job

logger = logging.getLogger(__name__)

# Countries of interest (for location filtering)
TARGET_COUNTRIES = {
    "morocco", "france", "germany", "netherlands", "belgium",
    "luxembourg", "poland", "switzerland", "uk", "united kingdom",
    "england", "remote", "europe",
}


class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        """Fetch jobs from Arbeitnow API and filter by keywords + location."""
        jobs = []
        pages = min(max_pages, ARBEITNOW_MAX_PAGES)

        now = datetime.now().isoformat()

        for page in range(1, pages + 1):
            logger.info(f"Fetching Arbeitnow page {page}...")
            try:
                resp = requests.get(
                    ARBEITNOW_API_URL,
                    params={"page": page},
                    headers={"User-Agent": "JobScraper/1.0"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"Arbeitnow API error on page {page}: {e}")
                break

            listings = data.get("data", [])
            if not listings:
                break

            for item in listings:
                title = item.get("title", "")
                company = item.get("company_name", "")
                location = item.get("location", "")
                tags = " ".join(item.get("tags", []))

                matched_keyword = match_job(title, tags, keywords)
                if not matched_keyword:
                    continue

                # Check location match (if regions specified)
                loc_lower = location.lower()
                if regions and "remote" not in [r.lower() for r in regions]:
                    location_match = any(
                        country in loc_lower for country in TARGET_COUNTRIES
                    ) or item.get("remote", False)
                    if not location_match:
                        continue

                # Determine region
                region = "remote" if item.get("remote", False) else "europe"
                for country in TARGET_COUNTRIES:
                    if country in loc_lower:
                        region = country
                        break

                jobs.append(Job(
                    title=title,
                    company=company,
                    location=location,
                    url=item.get("url", ""),
                    source="arbeitnow",
                    date_posted=item.get("created_at", ""),
                    description=item.get("description", "")[:500],
                    keyword=matched_keyword,
                    region=region,
                    scraped_at=now,
                ))

            self.delay(1, 2)

        logger.info(f"Arbeitnow: found {len(jobs)} matching jobs")
        return self.dedup(jobs)
