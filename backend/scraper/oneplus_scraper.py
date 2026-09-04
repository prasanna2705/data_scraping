"""OnePlus site adapter — only returns products when laptop listings exist."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from scraper.base import BaseScraper, domain_of, soup_of
from utils.feature_extraction import extract_features


class OnePlusScraper(BaseScraper):
    source_key = "oneplus"
    source_label = "OnePlus"

    def matches(self, query: str, url: str | None = None) -> bool:
        text = f"{query} {url or ''}".casefold()
        if url and "oneplus." in domain_of(url):
            return True
        return "oneplus" in text

    def search_url(self, query: str) -> str:
        # Prefer official laptop / pad category pages when available.
        text = (query or "").casefold()
        if "pad" in text:
            return "https://www.oneplus.in/oneplus-pad"
        return "https://www.oneplus.in/store?search=laptop"

    def extract_products(self, html: str, page_url: str) -> list[dict[str, Any]]:
        soup = soup_of(html)
        products: list[dict[str, Any]] = []
        candidates = soup.select("a, article, div.product, li")
        for node in candidates:
            text = node.get_text(" ", strip=True)
            if not text or len(text) < 8:
                continue
            if not self._looks_like_laptop(text):
                continue
            href = ""
            link = node if node.name == "a" else node.select_one("a")
            if link:
                href = link.get("href", "")
            title = (link.get_text(" ", strip=True) if link and link.get_text(strip=True) else text)[:180]
            price_match = re.search(r"₹\s*[\d,]+|Rs\.?\s*[\d,]+", text)
            price = price_match.group(0) if price_match else ""
            image = node.select_one("img")
            features = extract_features(title, price, "")
            features.update({
                "product_url": urljoin(page_url, href) if href else page_url,
                "image_url": image.get("src", "") if image else "",
                "source": self.source_label,
                "source_url": page_url,
            })
            if features.get("price"):
                products.append(features)

        # Deduplicate
        seen = set()
        unique = []
        for item in products:
            key = (item.get("title"), item.get("price"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    @staticmethod
    def _looks_like_laptop(text: str) -> bool:
        lowered = text.casefold()
        phone_noise = ("phone", "earphone", "buds", "watch", "charger", "case", "cable")
        if any(word in lowered for word in phone_noise) and "laptop" not in lowered:
            return False
        return any(word in lowered for word in ("laptop", "notebook", "chromebook", "pad"))
