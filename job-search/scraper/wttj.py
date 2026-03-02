import logging
from datetime import datetime
from urllib.parse import quote_plus

from .base import BaseScraper
from .config import WTTJ_BASE_URL, WTTJ_MAX_PAGES, WTTJ_DELAY_MIN, WTTJ_DELAY_MAX, match_job
from .models import Job

logger = logging.getLogger(__name__)


def _first(selector_list):
    """Return the first element or None."""
    return selector_list[0] if selector_list else None


class WTTJScraper(BaseScraper):
    """Scrape Welcome to the Jungle (WTTJ) job listings."""

    name = "wttj"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        from scrapling import Fetcher

        fetcher = Fetcher()
        jobs = []
        pages = min(max_pages, WTTJ_MAX_PAGES)
        now = datetime.now().isoformat()

        for keyword in keywords:
            for page in range(1, pages + 1):
                url = f"{WTTJ_BASE_URL}?query={quote_plus(keyword)}&page={page}"
                logger.info(f"WTTJ: '{keyword}' page {page}")

                try:
                    response = fetcher.get(url)
                    if response.status != 200:
                        logger.warning(f"WTTJ returned status {response.status} for {url}")
                        break

                    # WTTJ uses <li> elements with role="listitem" or article-based cards
                    cards = response.css('[data-testid="search-results-list-item-wrapper"]')
                    if not cards:
                        # Fallback selectors for WTTJ layout
                        cards = response.css("div[class*='SearchResults'] li")
                    if not cards:
                        cards = response.css("article")
                    if not cards:
                        logger.debug(f"No job cards found on page {page}")
                        break

                    for card in cards:
                        # Title from link or heading
                        title_el = _first(card.css("h4 a")) or _first(card.css("h3 a")) or _first(card.css("a[href*='/jobs/']"))
                        if not title_el:
                            continue

                        title = title_el.get_all_text().strip()
                        if not title:
                            continue

                        # Check keyword match
                        matched = match_job(title, "", keywords)
                        if not matched:
                            continue

                        # Job URL
                        job_href = title_el.attrib.get("href", "")
                        if job_href and not job_href.startswith("http"):
                            job_url = f"https://www.welcometothejungle.com{job_href}"
                        elif job_href:
                            job_url = job_href
                        else:
                            job_url = url

                        # Company name
                        company_el = _first(card.css("span[class*='company']")) or _first(card.css("h3")) or _first(card.css("p"))
                        company = company_el.get_all_text().strip() if company_el else ""

                        # Location
                        location_el = _first(card.css("span[class*='location']")) or _first(card.css("li[class*='location']"))
                        location = location_el.get_all_text().strip() if location_el else ""

                        # Contract type
                        contract_el = _first(card.css("span[class*='contract']")) or _first(card.css("li[class*='contract']"))
                        contract = contract_el.get_all_text().strip() if contract_el else ""

                        # Determine region from location
                        region = "france"
                        loc_lower = location.lower()
                        if any(c in loc_lower for c in ("maroc", "morocco", "casablanca", "rabat")):
                            region = "morocco"
                        elif any(c in loc_lower for c in ("germany", "berlin", "munich", "deutschland")):
                            region = "germany"
                        elif any(c in loc_lower for c in ("netherlands", "amsterdam", "rotterdam")):
                            region = "netherlands"
                        elif any(c in loc_lower for c in ("belgium", "brussels", "bruxelles")):
                            region = "belgium"
                        elif "remote" in loc_lower:
                            region = "remote"

                        description = f"{contract} - {location}" if contract else location

                        jobs.append(Job(
                            title=title,
                            company=company,
                            location=location,
                            url=job_url,
                            source="wttj",
                            date_posted="",
                            description=description,
                            keyword=matched,
                            region=region,
                            scraped_at=now,
                        ))

                    if len(cards) < 10:
                        break

                except Exception as e:
                    logger.error(f"WTTJ error ('{keyword}', page {page}): {e}")
                    break

                self.delay(WTTJ_DELAY_MIN, WTTJ_DELAY_MAX)

        logger.info(f"WTTJ: found {len(jobs)} jobs total")
        return self.dedup(jobs)
