# Mini Labs: YouTube Scraping Notes

Structured from:
- `internet_findings.md`
- `Screenshot 2026-03-07 223313.png`
- `Screenshot 2026-03-07 223323.png`
- `Screenshot 2026-03-07 223557.png`
- `Screenshot 2026-03-07 224414.png`

Run instructions:
- `RUN_GUIDE.md`

Selector guide:
- `HOW_TO_FIND_HTML_SELECTORS.md`

## Concept Map (ASCII)

```text
[Target URL]
     |
     v
[requests.get]
     |
     v
[HTML response]
     |
     v
[BeautifulSoup parse]
     |
     v
[select/find elements]
     |
     v
[extract fields: title, price, ...]
     |
     +------------------+
     |                  |
     v                  v
[print to console]   [write CSV/file]
     |
     v
[clean + filter + analyze]
```

## Website Defense / Scraper Strategy (ASCII)

```text
[Scraper]
   |
   +--> Pagination challenge ----> Iterate pages / crawler strategy
   |
   +--> JS-rendered content -----> Browser automation (e.g., Playwright)
   |
   +--> IP blocking / rate limit -> Proxy rotation / residential IP pool
```

## Labs

1. `lab_01_books_basic`
   - Basic `requests + BeautifulSoup`
   - Extract title + price from `books.toscrape.com`
2. `lab_02_books_csv`
   - Same extraction, then persist to CSV
3. `lab_03_github_proxy_concept`
   - Template for configurable scraping with proxy-aware request flow
