"""Flipkart laptop search extraction adapter."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus

from scraper.base import BaseScraper, domain_of, soup_of
from utils.feature_extraction import extract_features


class FlipkartScraper(BaseScraper):
    source_key = "flipkart"
    source_label = "Flipkart"

    def matches(self, query: str, url: str | None = None) -> bool:
        text = f"{query} {url or ''}".casefold()
        if url and "flipkart." in domain_of(url):
            return True
        return "flipkart" in text

    def search_url(self, query: str) -> str:
        phrase = re.sub(r"\bflipkart\.?\w*\b", " ", query or "", flags=re.I)
        phrase = re.sub(r"\s+", " ", phrase).strip(" -/") or "laptops"
        if "laptop" not in phrase.casefold():
            phrase = f"{phrase} laptops"
        return f"https://www.flipkart.com/search?q={quote_plus(phrase)}"

    def extract_products(self, html: str, page_url: str) -> list[dict[str, Any]]:
        soup = soup_of(html)
        products: list[dict[str, Any]] = []

        for card in soup.select("div[data-id], a._1fQZEK, div._2kHMtA, div._1AtVbE"):
            link = card if card.name == "a" else card.select_one("a")
            if not link:
                continue
            href = link.get("href", "")
            title_node = card.select_one("div._4rR01T, a.s1Q9rs, div.KzDlHZ")
            title = title_node.get_text(" ", strip=True) if title_node else link.get("title", "")
            if not title or not self._looks_like_laptop(title):
                continue
            product_url = href if href.startswith("http") else f"https://www.flipkart.com{href}"
            price_node = card.select_one("div._30jeq3, div.Nx9bqj, div._1_WHN1")
            price = price_node.get_text(" ", strip=True) if price_node else ""
            rating_node = card.select_one("div._3LWZlK, div.XQDdHH, div.gUuXy-")
            rating = rating_node.get_text(" ", strip=True) if rating_node else ""
            image = card.select_one("img")
            # Prefer high-res image when Flipkart embeds lazy src
            image_url = ""
            if image:
                image_url = image.get("src") or image.get("data-src") or ""
            features = extract_features(title, price, rating)
            features.update({
                "asin": card.get("data-id", ""),
                "product_url": product_url.split("?")[0],
                "image_url": image_url,
                "availability": "",
                "source": self.source_label,
                "source_url": page_url,
            })
            products.append(features)

        if products:
            # preserve order / uniqueness by URL
            seen = set()
            unique = []
            for item in products:
                key = item.get("product_url") or item.get("title")
                if key in seen:
                    continue
                seen.add(key)
                unique.append(item)
            return unique

        # JSON-LD product pages
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or "")
            except (TypeError, json.JSONDecodeError):
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") not in ("Product", ["Product"]):
                    continue
                title = str(item.get("name") or "")
                if not self._looks_like_laptop(title):
                    continue
                offers = item.get("offers", {}) if isinstance(item.get("offers"), dict) else {}
                rating = ""
                if isinstance(item.get("aggregateRating"), dict):
                    rating = item["aggregateRating"].get("ratingValue", "")
                features = extract_features(title, offers.get("price", ""), rating)
                features.update({
                    "product_url": page_url,
                    "image_url": str(item.get("image") or ""),
                    "source": self.source_label,
                    "source_url": page_url,
                })
                products.append(features)
        return products

    @staticmethod
    def _looks_like_laptop(title: str) -> bool:
        text = title.casefold()
        if any(word in text for word in ("bag", "cover", "charger", "mouse", "stand")):
            return False
        return any(word in text for word in ("laptop", "notebook", "chromebook", "macbook")) or (
            "gb" in text and re.search(r"\bi[3579]\b|ryzen", text)
        )
