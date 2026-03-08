import logging
import os
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from .config import (
    LINKEDIN_DELAY_MAX,
    LINKEDIN_DELAY_MIN,
    LINKEDIN_MAX_BYTES_PER_RUN,
    LINKEDIN_MAX_PAGES,
    LINKEDIN_REGIONS,
    LINKEDIN_RESULTS_PER_PAGE,
    match_job,
)
from .models import Job

logger = logging.getLogger(__name__)

_GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)


def _build_proxy_url() -> str | None:
    host = os.getenv("DATAIMPULSE_HOST")
    port = os.getenv("DATAIMPULSE_PORT")
    user = os.getenv("DATAIMPULSE_USER")
    passwd = os.getenv("DATAIMPULSE_PASS")
    if not all([host, port, user, passwd]):
        return None
    return f"http://{user}:{passwd}@{host}:{port}"


def _build_search_url(keyword: str, location: str, start: int = 0) -> str:
    url = f"{_GUEST_API}?keywords={quote_plus(keyword)}&location={quote_plus(location)}&start={start}"
    return url


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    def scrape(self, keywords: list[str], regions: list[str], max_pages: int) -> list[Job]:
        proxy_url = _build_proxy_url()
        if proxy_url:
            proxies = {"http": proxy_url, "https": proxy_url}
            logger.info("LinkedIn: using DataImpulse proxy")
        else:
            proxies = None
            logger.warning("LinkedIn: no proxy configured — may get rate-limited")

        headers = {"User-Agent": _USER_AGENT}
        pages = min(max_pages, LINKEDIN_MAX_PAGES)
        now = datetime.now().isoformat()
        jobs = []
        total_bytes = 0
        total_requests = 0

        target_regions = {
            name: loc for name, loc in LINKEDIN_REGIONS.items()
            if not regions or name in [r.lower() for r in regions]
        }

        budget_hit = False
        for region_name, location_query in target_regions.items():
            if budget_hit:
                break
            for keyword in keywords:
                if budget_hit:
                    break
                for page in range(pages):
                    start = page * LINKEDIN_RESULTS_PER_PAGE
                    url = _build_search_url(keyword, location_query, start)
                    logger.info(f"LinkedIn: {region_name} - '{keyword}' page {page + 1}")

                    try:
                        resp = requests.get(
                            url,
                            headers=headers,
                            proxies=proxies,
                            timeout=20,
                        )
                        total_bytes += len(resp.content)
                        total_requests += 1

                        if total_bytes >= LINKEDIN_MAX_BYTES_PER_RUN:
                            logger.warning(
                                f"LinkedIn: byte budget reached ({total_bytes / (1024*1024):.2f} MB "
                                f"/ {LINKEDIN_MAX_BYTES_PER_RUN / (1024*1024):.0f} MB). Stopping."
                            )
                            budget_hit = True
                            break

                        if resp.status_code == 429:
                            logger.warning("LinkedIn: rate-limited (429). Stopping this keyword.")
                            break
                        if resp.status_code != 200:
                            logger.warning(f"LinkedIn: status {resp.status_code} for {url}")
                            break

                        page_jobs = self._parse_cards(resp.text, keyword, region_name, keywords, now)
                        jobs.extend(page_jobs)

                        if len(page_jobs) == 0:
                            break

                    except Exception as e:
                        logger.error(f"LinkedIn error ({region_name}, '{keyword}', page {page + 1}): {e}")
                        break

                    self.delay(LINKEDIN_DELAY_MIN, LINKEDIN_DELAY_MAX)

        deduped = self.dedup(jobs)
        self._log_summary(deduped, total_requests, total_bytes, proxies is not None)
        return deduped

    @staticmethod
    def _log_summary(jobs: list[Job], requests_made: int, bytes_transferred: int, used_proxy: bool):
        mb = bytes_transferred / (1024 * 1024)
        gb = bytes_transferred / (1024 ** 3)
        logger.info(f"LinkedIn: {len(jobs)} jobs from {requests_made} requests ({mb:.2f} MB)")
        if used_proxy:
            cost_low = gb * 1.0   # $1/GB
            cost_high = gb * 5.0  # $5/GB
            logger.info(f"LinkedIn: proxy cost estimate: ${cost_low:.4f}–${cost_high:.4f} (at $1–$5/GB)")

    def _parse_cards(self, html: str, keyword: str, region: str,
                     all_keywords: list[str], now: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="base-search-card")
        jobs = []

        for card in cards:
            title_el = card.find("h3", class_="base-search-card__title")
            company_el = card.find("h4", class_="base-search-card__subtitle")
            location_el = card.find("span", class_="job-search-card__location")
            date_el = card.find("time")
            link_el = card.find("a", class_="base-card__full-link")

            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else region

            matched = match_job(title, "", all_keywords)
            if not matched:
                continue

            job_url = link_el.get("href", "").split("?")[0] if link_el else ""
            date_posted = date_el.get("datetime", "") if date_el else ""

            jobs.append(Job(
                title=title,
                company=company,
                location=location,
                url=job_url,
                source="linkedin",
                date_posted=date_posted,
                description="",
                keyword=matched,
                region=region,
                scraped_at=now,
            ))

        return jobs
