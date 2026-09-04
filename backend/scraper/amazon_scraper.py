"""Amazon India laptop search / product extraction adapter."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus

from scraper.base import BaseScraper, NoLaptopProductsError, domain_of, soup_of
from utils.feature_extraction import extract_features


class AmazonScraper(BaseScraper):
    source_key = "amazon"
    source_label = "Amazon"

    def matches(self, query: str, url: str | None = None) -> bool:
        text = f"{query} {url or ''}".casefold()
        if url and "amazon." in domain_of(url):
            return True
        return "amazon" in text

    def search_url(self, query: str) -> str:
        phrase = re.sub(r"\bamazon\.?\w*\b", " ", query or "", flags=re.I)
        phrase = re.sub(r"\s+", " ", phrase).strip(" -/") or "laptops"
        if "laptop" not in phrase.casefold():
            phrase = f"{phrase} laptop"
        return f"https://www.amazon.in/s?k={quote_plus(phrase)}"

    def extract_products(self, html: str, page_url: str) -> list[dict[str, Any]]:
        soup = soup_of(html)
        products: list[dict[str, Any]] = []

        # Search-result cards
        for card in soup.select("div[data-component-type='s-search-result'], div.s-result-item[data-asin]"):
            asin = (card.get("data-asin") or "").strip()
            if not asin:
                continue
            title_node = card.select_one("h2 a span, h2 span")
            title = title_node.get_text(" ", strip=True) if title_node else ""
            if not title or not self._looks_like_laptop(title):
                continue
            link = card.select_one("h2 a")
            href = link.get("href", "") if link else ""
            product_url = href if href.startswith("http") else f"https://www.amazon.in{href}" if href else f"https://www.amazon.in/dp/{asin}"
            price_node = card.select_one("span.a-price span.a-offscreen, span.a-price-whole")
            price = price_node.get_text(" ", strip=True) if price_node else ""
            rating_node = card.select_one("span.a-icon-alt")
            rating = rating_node.get_text(" ", strip=True) if rating_node else ""
            image = card.select_one("img.s-image")
            features = extract_features(title, price, rating)
            features.update({
                "asin": asin,
                "product_url": product_url.split("?")[0],
                "image_url": image.get("src", "") if image else "",
                "availability": "",
                "source": self.source_label,
                "source_url": page_url,
            })
            products.append(features)

        if products:
            return products

        # Single product page fallback
        title = ""
        title_node = soup.select_one("#productTitle, h1")
        if title_node:
            title = title_node.get_text(" ", strip=True)
        structured = {}
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or "")
            except (TypeError, json.JSONDecodeError):
                continue
            candidates = payload if isinstance(payload, list) else [payload]
            for item in candidates:
                if isinstance(item, dict) and item.get("@type") in ("Product", ["Product"]):
                    structured = item
                    break
        if not title:
            title = str(structured.get("name") or "").strip()
        if not title or not self._looks_like_laptop(title):
            return []
        offers = structured.get("offers", {}) if isinstance(structured.get("offers"), dict) else {}
        price_node = soup.select_one("span.a-price span.a-offscreen, #priceblock_ourprice")
        price = (price_node.get_text(" ", strip=True) if price_node else "") or offers.get("price", "")
        rating_node = soup.select_one("#acrPopover span.a-icon-alt, i.a-icon-star span.a-icon-alt")
        rating = rating_node.get_text(" ", strip=True) if rating_node else ""
        if not rating and isinstance(structured.get("aggregateRating"), dict):
            rating = structured["aggregateRating"].get("ratingValue", "")
        image = soup.select_one("#landingImage, #imgBlkFront")
        asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", page_url, re.I)
        features = extract_features(title, price, rating)
        features.update({
            "asin": asin_match.group(1).upper() if asin_match else "",
            "product_url": page_url,
            "image_url": image.get("src", "") if image else str(structured.get("image") or ""),
            "availability": "",
            "source": self.source_label,
            "source_url": page_url,
        })
        return [features]

    @staticmethod
    def _looks_like_laptop(title: str) -> bool:
        text = title.casefold()
        negatives = ("bag", "sleeve", "charger", "adapter", "cooling pad", "stand", "mouse", "skin", "cover")
        if any(word in text for word in negatives):
            return False
        positives = ("laptop", "notebook", "ultrabook", "macbook", "chromebook")
        if any(word in text for word in positives):
            return True
        # Amazon laptop SERP cards often omit the word "laptop" but include RAM/storage.
        return ("gb" in text) and any(token in text for token in ("ram", "ssd", "core i", "ryzen", "intel", "amd"))
