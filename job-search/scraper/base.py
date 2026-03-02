import logging
import random
import time
from abc import ABC, abstractmethod

from .models import Job

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all job scrapers."""

    name: str = "base"

    @abstractmethod
    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        """Scrape jobs matching the given keywords and regions."""
        ...

    @staticmethod
    def delay(min_sec: float, max_sec: float):
        """Sleep for a random duration between min_sec and max_sec."""
        wait = random.uniform(min_sec, max_sec)
        logger.debug(f"Sleeping {wait:.1f}s")
        time.sleep(wait)

    @staticmethod
    def dedup(jobs: list[Job]) -> list[Job]:
        """Remove duplicate jobs by URL."""
        seen = set()
        unique = []
        for job in jobs:
            if job.url not in seen:
                seen.add(job.url)
                unique.append(job)
        return unique
