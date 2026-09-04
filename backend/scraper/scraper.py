"""Amazon HTML helpers retained for unit tests and low-level extraction."""
from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from utils.feature_extraction import extract_features

LOGGER = logging.getLogger(__name__)
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "scraped" / "amazon" / "laptops.csv"
FIELDS = (
    "title", "price", "rating", "ram_gb", "storage_gb", "processor_score",
    "gpu_score", "screen_size", "brand", "recommended", "search_term",
    "asin", "product_url", "image_url", "availability", "storage_type", "cpu", "gpu",
    "processor", "source", "source_url", "scraped_at",
)


def is_amazon_product_url(value):
    try:
        parsed = urlparse(str(value).strip())
    except (TypeError, ValueError):
        return False
    is_amazon = parsed.hostname and (parsed.hostname == "amazon.in" or parsed.hostname.endswith(".amazon.in"))
    return parsed.scheme in {"http", "https"} and bool(is_amazon) and bool(parsed.path)


def extract_asin(url):
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", url, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _json_ld_product(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or "")
        except (TypeError, json.JSONDecodeError):
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if isinstance(item, dict) and (item.get("@type") == "Product" or item.get("@type") == ["Product"]):
                return item
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                for graph_item in item["@graph"]:
                    if isinstance(graph_item, dict) and graph_item.get("@type") == "Product":
                        return graph_item
    return {}


def _text(soup, *selectors):
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            value = node.get_text(" ", strip=True)
            if value:
                return value
    return ""


def extract_product(html, product_url):
    soup = BeautifulSoup(html, "html.parser")
    structured = _json_ld_product(soup)
    title = _text(soup, "#productTitle", "h1.a-size-large") or str(structured.get("name", "")).strip()
    if not title:
        raise RuntimeError("Amazon product name was not found; the page layout may have changed.")
    offers = structured.get("offers", {}) if isinstance(structured.get("offers", {}), dict) else {}
    price = _text(soup, "span.a-price span.a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice") or offers.get("price", "")
    rating = _text(soup, "#acrPopover span.a-icon-alt", "i.a-icon-star span.a-icon-alt")
    if not rating and isinstance(structured.get("aggregateRating"), dict):
        rating = structured["aggregateRating"].get("ratingValue", "")
    image = soup.select_one("#landingImage, #imgBlkFront")
    features = extract_features(title, price, rating)
    features.update({
        "asin": extract_asin(product_url),
        "product_url": product_url,
        "image_url": image.get("src", "") if image else str(structured.get("image", "") or ""),
        "availability": _text(soup, "#availability span") or str(offers.get("availability", "") or ""),
        "search_term": "amazon",
        "source": "Amazon",
        "processor": features.get("cpu") or "",
    })
    return features


def _read_rows(filename=DATA_PATH):
    path = Path(filename)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_rows(rows, filename=DATA_PATH):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def upsert_products(products, filename=DATA_PATH):
    rows = _read_rows(filename)
    by_key = {}
    for index, row in enumerate(rows):
        for key in (row.get("asin", ""), row.get("product_url", "")):
            if key:
                by_key[key] = index
    inserted = updated = 0
    for product in products:
        keys = [product.get("asin", ""), product.get("product_url", "")]
        index = next((by_key[key] for key in keys if key in by_key), None)
        if index is None:
            rows.append(product)
            index = len(rows) - 1
            inserted += 1
        else:
            rows[index].update(product)
            updated += 1
        for key in keys:
            if key:
                by_key[key] = index
    save_rows(rows, filename)
    return inserted, updated


def scrape_stored_products(filename=DATA_PATH):
    """Legacy no-op batch path — prefer /api/scrape with a query/URL."""
    return {
        "success": False,
        "message": "No Amazon URLs are available for scraping.",
        "total_urls": 0,
        "successful_urls": 0,
        "failed_urls": 0,
        "products_found": 0,
        "inserted": 0,
        "updated": 0,
    }


def fetch_page_selenium(url, timeout=20):
    raise RuntimeError("Selenium page fetch is disabled in favour of HTTP adapters.")
