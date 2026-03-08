from bs4 import BeautifulSoup
import requests
import csv


url = "https://books.toscrape.com"
response = requests.get(url, timeout=20)
print(response.status_code)

soup = BeautifulSoup(response.text, "html.parser")
books = soup.find_all("article", class_="product_pod")

with open("books.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Title", "Price"])

    for book in books:
        title = book.h3.a["title"]
        price = book.find("p", class_="price_color").text
        writer.writerow([title, price])

print("Saved: books.csv")
