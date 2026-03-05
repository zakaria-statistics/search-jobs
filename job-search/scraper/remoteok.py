import logging
from datetime import datetime

import requests

from .base import BaseScraper
from .config import REMOTEOK_API_URL, match_job
from .models import Job

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        """Fetch jobs from RemoteOK API and filter by keywords."""
        jobs = []
        logger.info("Fetching RemoteOK API...")

        try:
            resp = requests.get(
                REMOTEOK_API_URL,
                headers={"User-Agent": "JobScraper/1.0"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"RemoteOK API error: {e}")
            return jobs

        # First element is a metadata/legal notice object, skip it
        listings = data[1:] if len(data) > 1 else data

        now = datetime.now().isoformat()

        for item in listings:
            if not isinstance(item, dict) or "id" not in item:
                continue

            title = item.get("position", "")
            company = item.get("company", "")
            tags = " ".join(item.get("tags", []))
            description = item.get("description", "")

            matched_keyword = match_job(title, tags, keywords,
                                        description=description, lenient=True)
            if not matched_keyword:
                continue

            url = item.get("url", "")
            if not url and item.get("slug"):
                url = f"https://remoteok.com/remote-jobs/{item['slug']}"
            if not url:
                url = f"https://remoteok.com/remote-jobs/{item.get('id', '')}"

            jobs.append(Job(
                title=title,
                company=company,
                location=item.get("location", "Remote"),
                url=url,
                source="remoteok",
                date_posted=item.get("date", ""),
                description=description[:500] if description else "",
                keyword=matched_keyword,
                region="remote",
                scraped_at=now,
            ))

        logger.info(f"RemoteOK: found {len(jobs)} matching jobs")
        return self.dedup(jobs)
