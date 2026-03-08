# Lab 02: Books Scrape to CSV

## Goal
Reuse the same extraction logic, then save the data in a CSV file.

## Concept Flow (ASCII)

```text
[parsed book cards]
       |
       v
[extract title, price]
       |
       v
[normalize to row]
       |
       v
[csv.writer]
   |           |
   v           v
[header]   [data rows]
       \     /
        \   /
         v v
     [books.csv]
```

## Run

```bash
pip install requests beautifulsoup4
python book_scrape_to_csv.py
```
