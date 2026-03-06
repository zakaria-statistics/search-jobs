# Scraping Considerations & Lessons Learned

Practical notes from building scrapers for 5 job platforms. Each platform has its own quirks — this document captures what broke, what worked, and what to watch for.

---

## 0. CSR vs SSR — The First Question

Before writing a single line of scraper code, figure out how the target site renders its content. This determines your entire approach.

### Server-Side Rendering (SSR)

The HTML response from the server already contains the job data. You can parse it directly with an HTTP client + HTML parser.

**How to check:** `curl` the page URL (or view source in browser). If job titles, companies, and descriptions are visible in the raw HTML, it's SSR.

**Pros:** Fast, lightweight, no browser needed, low resource usage.
**Cons:** Must parse HTML (fragile CSS selectors), harder to handle pagination that requires form submissions.

**Our SSR scrapers:**
- **Rekrute** — Traditional HTML pages. `Fetcher` (basic HTTP + parsing) is sufficient. Job data is right in the HTML source.

### Client-Side Rendering (CSR)

The server returns a minimal HTML shell + JavaScript bundle. The actual job data is fetched by JS after page load (via API calls, usually XHR/fetch to a backend or third-party service).

**How to check:** `curl` the page and see mostly empty `<div id="root"></div>` with big JS bundles. Or view source vs rendered DOM — if they're very different, it's CSR.

**Pros (if you find the underlying API):** Much cleaner data, structured JSON instead of HTML parsing, faster and more reliable.
**Cons (if you scrape the rendered page):** Need a headless browser, slow, resource-heavy, anti-bot detection is harder to bypass.

**Our CSR scrapers and how we handle them:**

| Platform | Rendering | Our approach | Why |
|----------|-----------|-------------|-----|
| **Indeed** | CSR (React) | Headless browser (`StealthyFetcher`) | No public API. Must render JS to get job cards. Most expensive scraper. |
| **WTTJ** | CSR (React) | **Bypass the frontend entirely** — hit their Algolia API directly | Discovered WTTJ uses Algolia for search. The app ID and API key are public (embedded in frontend JS). We call Algolia directly and get clean JSON. No browser needed. |
| **RemoteOK** | SSR + API | REST API (`requests`) | They expose a public `/api` endpoint. No need to touch HTML at all. |
| **Arbeitnow** | SSR + API | REST API (`requests`) | Public job board API. Clean JSON responses. |
| **Rekrute** | SSR | HTML scraping (`Fetcher`) | Traditional server-rendered pages. Simple HTTP + CSS selectors. |

### The CSR Goldmine: Finding Hidden APIs

Most CSR sites load data from an API that the frontend calls. If you can find that API, you skip the browser entirely and get structured JSON.

**How to find hidden APIs:**
1. Open browser DevTools → Network tab
2. Filter by XHR/Fetch
3. Search or paginate on the site
4. Look for JSON responses containing job data
5. Copy the request (headers, params) and replay with `curl` or `requests`

**WTTJ example:** We discovered they use Algolia by watching Network requests. The search calls go to `*.algolia.net` with an app ID and API key visible in the request headers. We extracted those and now call Algolia directly — no browser, no HTML parsing, clean structured JSON with all job fields.

**Indeed anti-example:** Indeed's job data comes from server-rendered HTML that's hydrated by React. There's no clean API endpoint to hit (their internal APIs require auth tokens that rotate). We're stuck with headless browser scraping, which is 10x slower and more fragile.

### Decision Tree

```
Can you curl the page and see job data in HTML?
├── YES → SSR → Use simple HTTP client (requests/Fetcher)
│         Parse HTML with CSS selectors
│
└── NO → CSR → Open DevTools, find the API calls
          ├── Found a clean API? → Call it directly (requests)
          │   (WTTJ/Algolia, RemoteOK, Arbeitnow)
          │
          └── No accessible API? → Headless browser (StealthyFetcher)
              (Indeed — last resort, slowest option)
```

**Key lesson:** Always try to find the underlying API before reaching for a headless browser. CSR sites almost always have one — the frontend needs it to render. The API gives you cleaner data, runs faster, and is less likely to trigger anti-bot. Headless browser scraping should be the last resort.

---

## 1. Schema Mismatches (The #1 Problem)

Every platform returns data in a different shape. Field names change without warning, nested structures vary, and optional fields appear/disappear.

### WTTJ (Algolia API)

The biggest offender. WTTJ uses Algolia as their search backend, and the hit schema is deeply nested with inconsistent field presence:

| Field | Expected | Actual (sometimes) |
|-------|----------|---------------------|
| `name` | Job title string | Missing entirely on some hits |
| `organization.name` | Company name | `organization` can be `null` or `{}` |
| `office` | `{city, country_code}` dict | Can be `null`, `{}`, or a list |
| `profile` | Job description text | Empty string, `null`, or absent — fallback to `description` |
| `salary_minimum/maximum` | Integer | Float, string, or `null` |
| `remote` | `"fulltime"`, `"partial"` | `"unknown"`, empty string, `null` |
| `slug` / `organization.slug` | URL-safe string | Missing on some listings, breaks URL construction |
| `sectors` | `[{name: "..."}]` | Empty list, or objects missing `name` key |

**How we handle it:** Defensive `.get()` with fallbacks everywhere. For `office`, we check `isinstance(office, dict)` because it can be a list. For URLs, we have a fallback chain: `org_slug + job_slug` -> `reference` field -> empty string.

### Indeed (HTML Scraping)

Indeed's HTML structure changes periodically:

- CSS class `.job_seen_beacon` for job cards — could change any time
- `data-testid="company-name"` / `data-testid="text-location"` — these are test IDs, not stable contracts
- `h2.jobTitle a` — nesting depth can vary
- Description selector `#jobDescriptionText` has an alternative `.jobsearch-JobComponent-description`

**Lesson:** Always have fallback selectors. Check for `None` at every step (`_first()` helper). Log warnings instead of crashing when selectors miss.

### RemoteOK (JSON API)

- First element of the array is a legal notice / metadata object, not a job — must skip `data[1:]`
- `position` (not `title`) for job title
- `company` vs `company_name` (Arbeitnow uses `company_name`)
- `tags` is a list of strings, not a comma-separated string
- `url` can be empty — fallback to constructing from `slug` or `id`

### Arbeitnow (JSON API)

- Jobs live inside `data.data[]`, not top-level
- `company_name` (not `company`)
- `tags` is a list (like RemoteOK) but can contain empty strings
- `remote` is a boolean, not a string like WTTJ
- `created_at` (not `date_posted` or `published_at`)

**Takeaway:** Never assume two APIs use the same field names for the same concept. Create a mapping layer (our `Job` dataclass) that normalizes everything.

---

## 2. Anti-Bot & Rate Limiting

### Indeed

- Most aggressive anti-bot: requires headless browser (`StealthyFetcher`)
- Rate limits kick in fast — we use 5-10s random delays between pages
- Different country domains (`fr.indeed.com`, `de.indeed.com`) have different thresholds
- Enrichment (fetching full descriptions) needs 8-12s delays to avoid blocks
- Status 403/429 = back off, don't retry immediately

### WTTJ

- Uses Algolia, which is more lenient than direct scraping
- The API key is public (embedded in frontend JS), but Algolia tracks request volume
- 3-5s delay between pages is sufficient
- No headless browser needed

### RemoteOK / Arbeitnow

- Simple REST APIs with no auth required
- A `User-Agent` header is enough to avoid issues
- 1-2s delay between pages is plenty
- Rate limits are very generous — these are meant to be consumed programmatically

**Rule of thumb:** The closer you are to scraping rendered HTML, the more anti-bot you'll face. Prefer APIs and internal search endpoints when available.

---

## 3. URL Construction Pitfalls

### Broken URLs from Missing Fields

WTTJ URLs need both `organization.slug` and job `slug`. If either is missing, the URL 404s. We fall back to the `reference` field, but that produces a different URL format that may also break.

### Indeed's Relative URLs

Indeed job links are often relative (`/viewjob?jk=abc123`). Must prepend the correct domain: `https://fr.indeed.com/viewjob?jk=abc123`, not a generic `indeed.com`.

### RemoteOK Slug vs ID

Some jobs have `slug`, others only have `id`. URL format differs: `/remote-jobs/{slug}` vs `/remote-jobs/{id}`. Always try slug first.

**Practice:** Log jobs with empty/broken URLs. Validate URL format before saving. A job without a clickable link is useless in the tracker.

---

## 4. Location & Region Detection

Location data is the messiest field across all platforms:

| Platform | Format | Examples |
|----------|--------|----------|
| Indeed | Free text from page | "Paris (75)", "Île-de-France", "Berlin, Germany" |
| WTTJ | `office.city` + `office.country_code` | `{city: "Paris", country_code: "FR"}`, but can be `null` |
| RemoteOK | Usually just "Remote" | "Worldwide", "US/EU only", "" |
| Arbeitnow | Free text | "Berlin, Germany", "Remote - Europe", "Anywhere" |

Our `_detect_region()` in WTTJ does substring matching (`"amsterdam"` -> `netherlands`), but this is fragile — "NL" could match in unrelated strings. Indeed avoids this because the region comes from the domain we're querying.

**Watch out for:**
- Country codes vs full names ("DE" vs "Germany")
- Remote qualifiers ("Remote - France only", "Hybrid - Paris")
- Multi-location jobs ("Paris or Amsterdam")
- Missing location entirely (default to source's natural region)

---

## 5. Description Quality Varies Wildly

| Source | What you get | Quality |
|--------|-------------|---------|
| Indeed (search results) | 1-sentence snippet | Useless for ranking |
| Indeed (enriched) | Full HTML description | Good, but costs an extra request per job |
| WTTJ `profile` | Company profile blurb | Often about the company, not the role |
| WTTJ `description` | Sometimes has role details | Inconsistently populated |
| RemoteOK | Full HTML in API | Good, but can be very long (>5000 chars) |
| Arbeitnow | Full HTML in API | Good, similar to RemoteOK |

**What we do:**
- Truncate all descriptions to 500 chars during scraping
- `extract_skill_sentences()` picks skill-relevant lines instead of blind truncation during ranking
- Indeed enrichment fetches full page descriptions for the top 50 candidates
- For WTTJ, try `profile` first, fall back to `description`

**Lesson:** Don't trust raw descriptions for ranking. Extract the signal (skill keywords, requirements) and discard the noise (company mission statements, benefits lists).

---

## 6. Deduplication Challenges

Same job appears from multiple sources or multiple keyword searches:

- Indeed: "DevOps Engineer at Sopra" found via "DevOps Engineer" AND "Cloud Engineer" keywords, across `fr.indeed.com` and direct Indeed
- WTTJ: Same job returned for "DevOps" and "Platform Engineer" queries
- Cross-source: Same Sopra Steria job on Indeed AND WTTJ

Our dedup strategy: **URL-based** (`BaseScraper.dedup()` removes exact URL duplicates). This misses:
- Same job with different URL params (`?utm_source=indeed` vs clean URL)
- Same job on different platforms (Indeed vs WTTJ)

Cross-platform dedup would need fuzzy matching on (company + title + location), which we do at the ranking stage via Claude rather than in the scraper.

---

## 7. Date & Freshness Problems

| Platform | Date field | Format | Reliability |
|----------|-----------|--------|-------------|
| Indeed | Not directly available | — | Must infer from "Posted X days ago" text |
| WTTJ | `published_at` | ISO datetime | Reliable |
| RemoteOK | `date` | ISO datetime | Reliable |
| Arbeitnow | `created_at` | ISO datetime | Reliable |

Indeed is the worst — no reliable posted date in the search results HTML. The enrichment step doesn't reliably get it either. This makes "posted within last 7 days" filtering impossible for Indeed without extra parsing.

**Workaround:** We use `scraped_at` (when we found it) as a proxy. If a job appears in today's scrape but not yesterday's, it's probably new.

---

## 8. Keyword Matching: False Positives vs False Negatives

The core tension: cast too wide and you get noise (Java Developer matched because description mentions "cloud deployment"). Cast too narrow and you miss jobs with non-standard titles ("Infrastructure Reliability Specialist" = SRE).

Our 5-tier matching strategy addresses this:

1. **Exact phrase in title** — highest confidence, zero false positives
2. **Role terms in title** (`\bdevops\b`, `\bsre\b`) — good, but "cloud" in title catches too much
3. **Exact phrase in tags** — useful for WTTJ sectors
4. **Strict terms in tags** — only unambiguous terms (devops, kubernetes, sre)
5. **Lenient: 2+ skill keywords in description** — catches creative titles but risks noise

**Key decisions:**
- `\bsre\b` regex prevents matching "sre" inside German words like "un**sre**"
- "cloud" only matches in title (tier 2), never in tags alone (too broad)
- Lenient mode (tier 5) only enabled for API sources (RemoteOK, Arbeitnow, WTTJ) where we have full descriptions
- `count_skill_matches()` checks against 34 specific skill terms, not generic words

---

## 9. Error Handling Patterns

What actually fails in production:

| Failure | Frequency | Impact | Handling |
|---------|-----------|--------|----------|
| Network timeout | Common | Lose one page of results | `try/except`, log, continue to next page |
| Algolia API key rotated | Rare | WTTJ scraper fully breaks | Hard-coded key, must manually update from WTTJ frontend |
| Indeed HTML changed | Occasional | 0 jobs parsed, no error | Check job count = 0, log warning |
| Rate limited (403/429) | Common on Indeed | Lose remaining pages for that domain | Break out of page loop, move to next keyword/domain |
| Invalid JSON response | Rare | One API call fails | `try/except` around `resp.json()` |
| Empty API response | Occasional | No jobs for that query | Check `hits` empty, break pagination |

**Pattern:** Never let one page failure kill the entire scraper run. Log the error, skip that page/keyword, continue with the rest. The pipeline should always produce *some* results even if individual sources are degraded.

---

## 10. Checklist for Adding a New Scraper

When adding a new job platform:

0. **rendering method** - Is the website crs or ssr
1. **Identify the data source** — Is there a public API? An internal search API (like Algolia)? Or HTML-only?
2. **Map the schema** — Document every field name and type. Print a raw response and study it before writing any parsing code.
3. **Handle `null`/missing** — Every `.get()` needs a default. Every nested access needs a guard.
4. **Build URLs carefully** — Test generated URLs in a browser. Check for encoding issues.
5. **Match the `Job` dataclass** — Map platform fields to our normalized model. Don't invent new fields.
6. **Test edge cases** — What happens with 0 results? With the last page? With a rate limit?
7. **Add to `match_job()`** — Decide if this source gets lenient matching (needs full descriptions) or strict only.
8. **Set appropriate delays** — API sources: 1-2s. HTML scraping: 5-10s. Headless browser: 8-12s.
9. **Test dedup** — Run the same query twice and verify no duplicates in output.
10. **Document the quirks** — Add a section to this file.