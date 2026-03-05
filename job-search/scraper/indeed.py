import logging
from datetime import datetime

from .base import BaseScraper
from .config import (
    INDEED_DELAY_MAX,
    INDEED_DELAY_MIN,
    INDEED_ENRICH_DELAY_MAX,
    INDEED_ENRICH_DELAY_MIN,
    INDEED_ENRICH_MAX,
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

    def enrich(self, jobs: list[dict], max_jobs: int = None) -> list[dict]:
        """Fetch full descriptions for Indeed jobs with short/empty descriptions.

        Modifies jobs in-place and returns the full list.
        """
        from scrapling import StealthyFetcher
        from .description_utils import extract_skill_sentences

        if max_jobs is None:
            max_jobs = INDEED_ENRICH_MAX

        # Filter to Indeed jobs needing enrichment (short descriptions)
        candidates = [
            j for j in jobs
            if j.get("source") == "indeed" and len(j.get("description", "")) < 100
        ]
        to_enrich = candidates[:max_jobs]

        if not to_enrich:
            logger.info("Indeed enrich: no jobs need enrichment")
            return jobs

        logger.info(f"Indeed enrich: enriching {len(to_enrich)}/{len(candidates)} candidates")
        fetcher = StealthyFetcher()
        enriched = 0

        for i, job in enumerate(to_enrich, 1):
            url = job.get("url", "")
            if not url:
                continue

            logger.info(f"  Enriching {i}/{len(to_enrich)}: {job.get('title', '?')[:50]}")
            try:
                response = fetcher.fetch(url, headless=True, disable_resources=True)
                if response.status != 200:
                    logger.warning(f"  Status {response.status} for {url}")
                    self.delay(INDEED_ENRICH_DELAY_MIN, INDEED_ENRICH_DELAY_MAX)
                    continue

                # Try known description selectors
                desc_el = _first(response.css("#jobDescriptionText"))
                if not desc_el:
                    desc_el = _first(response.css(".jobsearch-JobComponent-description"))

                if desc_el:
                    raw_html = desc_el.html_content if hasattr(desc_el, 'html_content') else desc_el.get_all_text()
                    skill_text = extract_skill_sentences(raw_html)
                    if skill_text:
                        job["description"] = skill_text
                        enriched += 1
                        logger.info(f"  Enriched ({len(skill_text)} chars)")
                    else:
                        # Fall back to full text truncated
                        full_text = desc_el.get_all_text().strip()
                        if full_text:
                            job["description"] = full_text[:800]
                            enriched += 1

            except Exception as e:
                logger.error(f"  Enrich error: {e}")

            self.delay(INDEED_ENRICH_DELAY_MIN, INDEED_ENRICH_DELAY_MAX)

        logger.info(f"Indeed enrich: enriched {enriched}/{len(to_enrich)} jobs")
        return jobs
