"""Fallback scraper for unknown domains — never invents products."""
from __future__ import annotations

from typing import Any

from scraper.base import BaseScraper, UnsupportedSourceError


class GenericScraper(BaseScraper):
    source_key = "custom"
    source_label = "Custom"

    def matches(self, query: str, url: str | None = None) -> bool:
        return False

    def search_url(self, query: str) -> str:
        raise UnsupportedSourceError(
            "This website is not currently supported for structured laptop scraping."
        )

    def extract_products(self, html: str, page_url: str) -> list[dict[str, Any]]:
        return []

    def scrape(self, query: str, url: str | None = None, max_products: int = 48) -> list[dict[str, Any]]:
        raise UnsupportedSourceError(
            "This website is not currently supported for structured laptop scraping."
        )
