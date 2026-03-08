import re

KEYWORDS = [
    "DevOps Engineer",
    "Cloud Engineer",
    "MLOps Engineer",
    "Platform Engineer",
    "Site Reliability Engineer",
    "Kubernetes Engineer",
    "AI Infrastructure Engineer",
    "Cloud Architect",
]

# Region name -> Indeed domain + default location query
REGIONS = {
    "morocco": {"domain": "ma.indeed.com", "location": ""},
    "france": {"domain": "fr.indeed.com", "location": ""},
    "germany": {"domain": "de.indeed.com", "location": ""},
    "netherlands": {"domain": "nl.indeed.com", "location": ""},
    "belgium": {"domain": "be.indeed.com", "location": ""},
    "luxembourg": {"domain": "lu.indeed.com", "location": ""},
    "poland": {"domain": "pl.indeed.com", "location": ""},
    "switzerland": {"domain": "ch.indeed.com", "location": ""},
    "uk": {"domain": "uk.indeed.com", "location": ""},
}

# Platform settings
INDEED_MAX_PAGES = 3
INDEED_DELAY_MIN = 5
INDEED_DELAY_MAX = 10
INDEED_RESULTS_PER_PAGE = 10

REKRUTE_MAX_PAGES = 3
REKRUTE_DELAY_MIN = 2
REKRUTE_DELAY_MAX = 5

REMOTEOK_API_URL = "https://remoteok.com/api"
ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"
ARBEITNOW_MAX_PAGES = 15

# WTTJ (Welcome to the Jungle) settings
WTTJ_BASE_URL = "https://www.welcometothejungle.com/fr/jobs"
WTTJ_MAX_PAGES = 3
WTTJ_DELAY_MIN = 3
WTTJ_DELAY_MAX = 5

# Indeed enrichment settings
INDEED_ENRICH_MAX = 50
INDEED_ENRICH_DELAY_MIN = 8
INDEED_ENRICH_DELAY_MAX = 12

# LinkedIn settings (uses DataImpulse proxy)
LINKEDIN_RESULTS_PER_PAGE = 25
LINKEDIN_MAX_PAGES = 3
LINKEDIN_DELAY_MIN = 4
LINKEDIN_DELAY_MAX = 8
LINKEDIN_MAX_BYTES_PER_RUN = 10 * 1024 * 1024  # 10 MB

LINKEDIN_REGIONS = {
    "morocco": "Morocco",
    "france": "France",
    "germany": "Germany",
    "netherlands": "Netherlands",
    "belgium": "Belgium",
    "luxembourg": "Luxembourg",
    "poland": "Poland",
    "switzerland": "Switzerland",
    "uk": "United Kingdom",
}

# URL validation settings
URL_VALIDATE_DELAY_MIN = 3
URL_VALIDATE_DELAY_MAX = 6
URL_VALIDATE_MAX_JOBS = 200

# Output directory (relative to job-search/)
OUTPUT_DIR = "output"

# Terms that are strong signals when found as whole words in the TITLE.
TITLE_TERMS = [
    r"\bdevops\b", r"\bdev\s*ops\b",
    r"\bcloud\b",
    r"\bmlops\b", r"\bml\s*ops\b",
    r"\bsre\b",
    r"\bplatform\b",
    r"\bkubernetes\b", r"\bk8s\b",
    r"\binfrastructure\b",
    r"\bsite.reliability\b",
]

_TITLE_PATTERN = re.compile("|".join(TITLE_TERMS), re.IGNORECASE)


def match_job(title: str, tags: str, keywords: list[str],
              description: str = "", lenient: bool = False) -> str | None:
    """Return the matched keyword/term or None.

    Matching strategy:
      1. Full keyword phrase in title  (e.g. "DevOps Engineer" in title)
      2. Role-specific terms as whole words in title
      3. Full keyword phrase in tags
      4. Role-specific terms as whole words in tags
      5. (lenient only) Description contains 2+ skill keywords
    Title matches are preferred — tag-only matches use a stricter set to
    reduce noise from broad tags like "cloud".
    """
    title_lower = title.lower()
    tags_lower = tags.lower()

    # 1. Full phrase in title
    for kw in keywords:
        if kw.lower() in title_lower:
            return kw

    # 2. Role terms in title (whole-word)
    m = _TITLE_PATTERN.search(title_lower)
    if m:
        return m.group()

    # 3. Full phrase in tags
    for kw in keywords:
        if kw.lower() in tags_lower:
            return kw

    # 4. Role terms in tags — but only the unambiguous ones
    tag_pattern = re.compile(
        r"\bdevops\b|\bmlops\b|\bsre\b|\bkubernetes\b|\bk8s\b|\bsite.reliability\b|\binfrastructure.engineer\b",
        re.IGNORECASE,
    )
    m = tag_pattern.search(tags_lower)
    if m:
        return m.group()

    # 5. Lenient: description contains 2+ skill keywords
    if lenient and description:
        from .description_utils import count_skill_matches
        if count_skill_matches(description) >= 2:
            return "skill-match"

    return None


def build_indeed_url(domain: str, keyword: str, location: str, start: int = 0) -> str:
    from urllib.parse import quote_plus
    url = f"https://{domain}/jobs?q={quote_plus(keyword)}&l={quote_plus(location)}"
    if start > 0:
        url += f"&start={start}"
    return url


def build_rekrute_url(keyword: str, page: int = 1) -> str:
    from urllib.parse import quote_plus
    return f"https://www.rekrute.com/offres.html?s=3&p={page}&o=1&keyword={quote_plus(keyword)}"
