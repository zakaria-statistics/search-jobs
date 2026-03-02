import logging
from datetime import datetime

from .base import BaseScraper
from .config import (
    INDEED_DELAY_MAX,
    INDEED_DELAY_MIN,
    INDEED_MAX_PAGES,
    INDEED_RESULTS_PER_PAGE,
    REGIONS,
    build_indeed_url,
)
from .models import Job

logger = logging.getLogger(__name__)


def _first(selector_list):
    """Return the first element or None (replaces css_first)."""
    return selector_list[0] if selector_list else None


class IndeedScraper(BaseScraper):
    name = "indeed"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        """Scrape Indeed job listings using StealthyFetcher."""
        from scrapling import StealthyFetcher

        fetcher = StealthyFetcher()
        jobs = []
        pages = min(max_pages, INDEED_MAX_PAGES)
        now = datetime.now().isoformat()

        target_regions = {
            name: info for name, info in REGIONS.items()
            if not regions or name in [r.lower() for r in regions]
        }

        for region_name, region_info in target_regions.items():
            domain = region_info["domain"]
            location = region_info["location"]

            for keyword in keywords:
                for page in range(pages):
                    start = page * INDEED_RESULTS_PER_PAGE
                    url = build_indeed_url(domain, keyword, location, start)
                    logger.info(f"Indeed: {region_name} - '{keyword}' page {page + 1}")

                    try:
                        response = fetcher.fetch(url, headless=True, disable_resources=True)
                        if response.status != 200:
                            logger.warning(f"Indeed returned status {response.status} for {url}")
                            break

                        job_cards = response.css(".job_seen_beacon")
                        if not job_cards:
                            logger.debug(f"No job cards found on page {page + 1}")
                            break

                        for card in job_cards:
                            title_el = _first(card.css("h2.jobTitle a"))
                            company_el = _first(card.css('[data-testid="company-name"]'))
                            location_el = _first(card.css('[data-testid="text-location"]'))
                            snippet_el = _first(card.css(".underShelfFooter"))

                            title = title_el.get_all_text().strip() if title_el else ""
                            if not title:
                                continue

                            # Build job URL
                            job_href = title_el.attrib.get("href", "") if title_el else ""
                            if job_href and not job_href.startswith("http"):
                                job_url = f"https://{domain}{job_href}"
                            elif job_href:
                                job_url = job_href
                            else:
                                job_url = url

                            jobs.append(Job(
                                title=title,
                                company=company_el.get_all_text().strip() if company_el else "",
                                location=location_el.get_all_text().strip() if location_el else region_name,
                                url=job_url,
                                source="indeed",
                                date_posted="",
                                description=snippet_el.get_all_text().strip()[:500] if snippet_el else "",
                                keyword=keyword,
                                region=region_name,
                                scraped_at=now,
                            ))

                        if len(job_cards) < INDEED_RESULTS_PER_PAGE:
                            break

                    except Exception as e:
                        logger.error(f"Indeed error ({region_name}, '{keyword}', page {page + 1}): {e}")
                        break

                    self.delay(INDEED_DELAY_MIN, INDEED_DELAY_MAX)

        logger.info(f"Indeed: found {len(jobs)} jobs total")
        return self.dedup(jobs)
