import logging
from datetime import datetime

from .base import BaseScraper
from .config import REKRUTE_DELAY_MAX, REKRUTE_DELAY_MIN, REKRUTE_MAX_PAGES, build_rekrute_url
from .models import Job

logger = logging.getLogger(__name__)


def _first(selector_list):
    """Return the first element or None (replaces css_first)."""
    return selector_list[0] if selector_list else None


class RekruteScraper(BaseScraper):
    name = "rekrute"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        """Scrape Rekrute.com job listings."""
        # Rekrute is Morocco-only; skip if regions specified and morocco not included
        if regions and "morocco" not in [r.lower() for r in regions]:
            logger.info("Rekrute: skipped (morocco not in target regions)")
            return []

        from scrapling import Fetcher

        fetcher = Fetcher()
        jobs = []
        pages = min(max_pages, REKRUTE_MAX_PAGES)
        now = datetime.now().isoformat()

        for keyword in keywords:
            for page in range(1, pages + 1):
                url = build_rekrute_url(keyword, page)
                logger.info(f"Rekrute: '{keyword}' page {page}")

                try:
                    response = fetcher.get(url)
                    if response.status != 200:
                        logger.warning(f"Rekrute returned status {response.status}")
                        break

                    cards = response.css(".post-id")
                    if not cards:
                        logger.debug(f"No cards found on page {page}")
                        break

                    for card in cards:
                        title_el = _first(card.css("a.titreJob")) or _first(card.css("h2 a"))
                        company_el = _first(card.css("img.photo"))
                        location_el = _first(card.css(".location")) or _first(card.css(".info span"))
                        date_el = _first(card.css(".date")) or _first(card.css("em"))

                        title = title_el.get_all_text().strip() if title_el else ""
                        if not title:
                            continue

                        job_href = title_el.attrib.get("href", "") if title_el else ""
                        if job_href and not job_href.startswith("http"):
                            job_url = f"https://www.rekrute.com{job_href}"
                        elif job_href:
                            job_url = job_href
                        else:
                            job_url = url

                        company = ""
                        if company_el:
                            company = company_el.attrib.get("alt", "") or company_el.get_all_text() or ""
                            company = company.strip()

                        jobs.append(Job(
                            title=title,
                            company=company,
                            location=location_el.get_all_text().strip() if location_el else "Morocco",
                            url=job_url,
                            source="rekrute",
                            date_posted=date_el.get_all_text().strip() if date_el else "",
                            description="",
                            keyword=keyword,
                            region="morocco",
                            scraped_at=now,
                        ))

                    if len(cards) < 10:
                        break

                except Exception as e:
                    logger.error(f"Rekrute error ('{keyword}', page {page}): {e}")
                    break

                self.delay(REKRUTE_DELAY_MIN, REKRUTE_DELAY_MAX)

        logger.info(f"Rekrute: found {len(jobs)} jobs total")
        return self.dedup(jobs)
