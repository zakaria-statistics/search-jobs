# Lab 03: GitHub Trending + Proxy Concept

## Goal
Turn the screenshot and notes into a configurable template:
- fetch all-time top-starred repos by category (`devops`, `cloud`, `ai/mlops`, `automation`, `agents`)
- optional proxy config
- save a 20-repo JSON snapshot
- track transferred bytes and estimated proxy cost
- apply a reasonable byte-transfer rate limit

## Request Strategy (ASCII)

```text
            [Config]
               |
               v
    +----------------------+
    | URL + headers + TLS |
    +----------------------+
               |
      +--------+--------+
      |                 |
      v                 v
[No proxy path]   [Proxy path]
      |                 |
      +--------+--------+
               |
               v
        [requests.get()]
               |
               v
       [BeautifulSoup parse]
               |
               v
        [repo list output]
```

## Defense Notes (ASCII)

```text
[Blocking risk]
   |
   +--> low: public static page
   +--> medium: pagination + heavy volume
   +--> high: JS + rate limiting + fingerprint checks

Mitigation ladder:
1) polite request rate + timeout/retry
2) browser rendering for JS pages
3) proxy rotation / residential IP pool
```

## Run

```bash
pip install requests beautifulsoup4
python github_trending_template.py
```

## Output

- JSON file: `github_all_time_top20.json`
- Includes:
  - `results` (max 20 repos)
  - `byte_rate_limit` config used
  - `traffic` section with request/response/total bytes
  - optional `estimated_proxy_cost_usd` (set `PROXY_PRICE_PER_GB_USD`)
