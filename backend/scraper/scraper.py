"""Amazon-only scraper for product URLs already stored in the catalog CSV."""
import csv
import json
import logging
import random
import re
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.feature_extraction import extract_features

LOGGER = logging.getLogger(__name__)
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "laptops.csv"
PROFILE_ROOT = Path(__file__).resolve().parents[1] / ".selenium-profiles"
FIELDS = ("title", "price", "rating", "ram_gb", "storage_gb", "processor_score",
          "gpu_score", "screen_size", "brand", "recommended", "search_term",
          "asin", "product_url", "image_url", "availability")


def is_amazon_product_url(value):
    """Accept only HTTP(S) Amazon India product URLs; never accept arbitrary URLs."""
    try:
        parsed = urlparse(str(value).strip())
    except (TypeError, ValueError):
        return False
    is_amazon = parsed.hostname and (parsed.hostname == "amazon.in" or parsed.hostname.endswith(".amazon.in"))
    return parsed.scheme in {"http", "https"} and bool(is_amazon) and bool(parsed.path)


def extract_asin(url):
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", url, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def stored_amazon_urls(filename=DATA_PATH):
    """Read product URLs from the existing catalog storage, without inventing any."""
    path = Path(filename)
    if not path.exists():
        return [], 0
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    urls = [str(row.get("product_url") or "").strip() for row in rows if str(row.get("product_url") or "").strip()]
    return urls, len(urls)


def chrome_options(profile_dir):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument(f"--user-data-dir={profile_dir}")
    return options


def fetch_page_selenium(url, timeout=20):
    """Fetch one stored URL with an isolated profile and guaranteed driver cleanup."""
    PROFILE_ROOT.mkdir(exist_ok=True)
    profile_dir = tempfile.mkdtemp(prefix="scrape-", dir=PROFILE_ROOT)
    driver = None
    try:
        # Selenium Manager selects the matching locally cached/installed driver.
        driver = webdriver.Chrome(options=chrome_options(profile_dir))
        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#productTitle, #ppd")))
        return driver.page_source
    except TimeoutException as exc:
        raise RuntimeError("Amazon product content did not load in time.") from exc
    except WebDriverException as exc:
        LOGGER.debug("Chrome failure for %s", url, exc_info=True)
        raise RuntimeError("Selenium could not start Chrome or open Amazon. Close Chrome and retry.") from exc
    finally:
        if driver is not None:
            driver.quit()
        try:
            shutil.rmtree(profile_dir)
        except OSError as error:
            LOGGER.warning("Could not remove temporary Chrome profile %s: %s", profile_dir, error)


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
    """Extract a resilient subset of product-page data; missing fields are safe."""
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
        "search_term": "stored_amazon_url",
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
    """Update existing ASIN/URL rows and add new products without duplicates."""
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
    """Scrape every valid stored Amazon URL; a failed URL never stops the batch."""
    urls, total_urls = stored_amazon_urls(filename)
    if not urls:
        return {"success": False, "message": "No Amazon URLs are available for scraping.", "total_urls": 0, "successful_urls": 0, "failed_urls": 0, "products_found": 0, "inserted": 0, "updated": 0}
    products, successful, failed = [], 0, 0
    for url in urls:
        if not is_amazon_product_url(url):
            LOGGER.warning("Skipping invalid/non-Amazon stored URL: %s", url)
            failed += 1
            continue
        try:
            products.append(extract_product(fetch_page_selenium(url), url))
            successful += 1
        except RuntimeError as error:
            failed += 1
            LOGGER.warning("Stored URL scrape failed for %s: %s", url, error)
        time.sleep(random.uniform(1, 2))
    inserted, updated = upsert_products(products, filename) if products else (0, 0)
    success = successful > 0
    message = "Scraping completed successfully" if failed == 0 else "Scraping completed with some errors" if success else "Scraping failed"
    return {"success": success, "message": message, "total_urls": total_urls, "successful_urls": successful, "failed_urls": failed, "products_found": len(products), "inserted": inserted, "updated": updated}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(scrape_stored_products())
