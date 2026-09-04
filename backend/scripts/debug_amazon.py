from bs4 import BeautifulSoup

from scraper.amazon_scraper import AmazonScraper
from scraper.base import fetch_html

s = AmazonScraper()
url = s.search_url("laptops")
print("URL", url)
html = fetch_html(url)
print("html len", len(html))
print("blocked signals", "captcha" in html.lower(), "api-services-support@amazon" in html.lower())
products = s.extract_products(html, url)
print("products", len(products))
for p in products[:10]:
    print("-", (p.get("title") or "")[:90], p.get("price"))
soup = BeautifulSoup(html, "html.parser")
cards = soup.select("div[data-component-type='s-search-result'], div.s-result-item[data-asin]")
print("cards", len(cards))
print("with asin", sum(1 for c in cards if (c.get("data-asin") or "").strip()))
