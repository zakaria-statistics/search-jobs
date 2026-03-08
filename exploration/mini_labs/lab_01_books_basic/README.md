# Lab 01: Books Basic Scrape

## Goal
Fetch `https://books.toscrape.com`, parse product cards, and print:
- title
- price

## Concept Flow (ASCII)

```text
[books.toscrape.com]
        |
        v
[HTTP GET request]
        |
        v
[status code check]
        |
        v
[BeautifulSoup(html.parser)]
        |
        v
[find_all("article", class_="product_pod")]
        |
        v
[for each book]
   |                |
   v                v
[title attr]     [price text]
        \          /
         \        /
          v      v
      [print row]
```

## Run

```bash
pip install requests beautifulsoup4
python book_scrape_print.py
```
