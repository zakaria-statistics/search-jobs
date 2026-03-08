# Run Guide for Mini Labs

This guide shows how to run all scripts in:
- `lab_01_books_basic`
- `lab_02_books_csv`
- `lab_03_github_proxy_concept`

## 1) Prerequisites

- Python 3.10+ installed
- Internet access for live requests

Check Python:

```bash
python3 --version
```

## 2) Move to the mini_labs folder

```bash
cd /root/search/exploration/youtube_tutorials/scraping/mini_labs
```

## 3) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4) Install dependencies

```bash
pip install requests beautifulsoup4
```

## 5) Run each lab

### Lab 01: Print book title + price

```bash
cd lab_01_books_basic
python3 book_scrape_print.py
```

Expected:
- HTTP status code (usually `200`)
- list of `Title - Price`

### Lab 02: Save books to CSV

```bash
cd ../lab_02_books_csv
python3 book_scrape_to_csv.py
```

Expected:
- HTTP status code
- `Saved: books.csv`
- output file at:
  `lab_02_books_csv/books.csv`

### Lab 03: GitHub trending template

```bash
cd ../lab_03_github_proxy_concept
python3 github_trending_template.py
```

Expected:
- `Fetched <N> repos from: <url>`
- top repo names

## 6) Optional: proxy configuration for Lab 03

Edit:
- `lab_03_github_proxy_concept/github_trending_template.py`

Update the `PROXY` object:

```python
PROXY = {
    "host": "gw.example.com",
    "port": "823",
    "username": "YOUR_USER",
    "password": "YOUR_PASS",
}
```

Set `PROXY = None` to disable proxy.

## 7) Troubleshooting

- If `python` is not found, use `python3`.
- If SSL/proxy issues appear, keep `VERIFY_SSL = True` unless you know why to change it.
- If requests fail intermittently, retry after a short wait to reduce rate-limit pressure.
