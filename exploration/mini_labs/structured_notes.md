# Structured Notes (from `internet_findings.md`)

## Source
- Video: `Learn Web Scraping in 5 Minutes (NO PRIOR KNOWLEDGE)` by CodeHead
- URL: `https://www.youtube.com/watch?v=hHQlcnubuFI`

## Core Stack
- `requests`: fetch page content
- `beautifulsoup4`: parse HTML and extract fields
- `csv`: persist extracted rows

## End-to-End Pipeline

```text
[target source]
    ->
[scraping script]
    ->
[saved raw data]
    ->
[clean + organize]
    ->
[filter/sort/insight]
    ->
[share/export to analysis tools]
```

## Practical Constraints
- Friendly practice target: `https://books.toscrape.com`
- Real-world friction:
  - pagination complexity
  - JavaScript-rendered content
  - IP blocking / rate limiting

## Tooling Ideas Mentioned In Notes
- Browser rendering option: Playwright
- Crawling framework option: Scrapy
- Proxy pool option: managed provider (example noted: DataImpulse)
