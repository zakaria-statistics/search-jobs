# How To Find HTML/CSS Element Names For Scraping

Question example:

```python
books = soup.find_all("article", class_="product_pod")
```

How do we know `"article"` and `"product_pod"`?

## 1) Inspect the page in browser

1. Open the target page (example: `https://books.toscrape.com`).
2. Right click the element you want (a book card) and click **Inspect**.
3. In DevTools, look at the HTML around that element.

You will usually see something like:

```html
<article class="product_pod">
  ...
</article>
```

From this:
- tag name = `article`
- class name = `product_pod`

So in BeautifulSoup:

```python
soup.find_all("article", class_="product_pod")
```

## 2) Find child fields inside each card

Inside each `article.product_pod`, inspect title and price:

```html
<h3><a title="A Light in the Attic" ...>...</a></h3>
<p class="price_color">£51.77</p>
```

That is why script lines become:

```python
title = book.h3.a["title"]
price = book.find("p", class_="price_color").text
```

## 3) Selector patterns to know

- By tag: `soup.find_all("article")`
- By class: `soup.find_all(class_="product_pod")`
- By tag + class: `soup.find_all("article", class_="product_pod")`
- By id: `soup.find(id="main")`
- CSS selector style: `soup.select("article.product_pod p.price_color")`

## 4) Fast workflow for any website

1. Pick one data point you need (title, price, date, etc.).
2. Inspect element in DevTools.
3. Identify stable selector (id/class/tag combination).
4. Test selector in Python with a small print.
5. Repeat for each field.

## 5) Important real-world note

Some websites render content with JavaScript, so raw `requests.get(url).text` may not include the final HTML you see in browser.  
In that case, use browser automation tools (like Playwright) or framework-based crawlers for JS-heavy pages.
