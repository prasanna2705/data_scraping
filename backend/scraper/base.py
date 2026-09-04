"""Shared HTTP helpers and base scraper interface."""
from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class ScrapeBlockedError(RuntimeError):
    """Raised when a site blocks automated access."""


class UnsupportedSourceError(RuntimeError):
    """Raised when no scraper can handle the requested source."""


class ComingSoonError(RuntimeError):
    """Raised when a known retailer is not enabled in this version."""


class NoLaptopProductsError(RuntimeError):
    """Raised when a site has no compatible laptop products."""


def domain_of(url: str) -> str:
    try:
        host = (urlparse(str(url).strip()).hostname or "").lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def fetch_html(url: str, timeout: int = 20) -> str:
    """Fetch a page with polite headers. Does not bypass CAPTCHA/login/blocks."""
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        raise ScrapeBlockedError(
            "The website could not be reached for automated collection. "
            "Please try another supported source or URL."
        ) from exc

    body = response.text or ""
    lowered = body.casefold()
    blocked_signals = (
        "captcha", "robot check", "enter the characters", "api-services-support@amazon",
        "validatecaptcha", "access denied", "unusual traffic",
    )
    if response.status_code in {401, 403, 429, 503} or any(signal in lowered for signal in blocked_signals):
        raise ScrapeBlockedError(
            "This website currently prevents automated scraping. "
            "Please try another supported source."
        )
    if response.status_code >= 400:
        raise ScrapeBlockedError(
            f"The website returned HTTP {response.status_code}. "
            "Automated collection could not continue."
        )
    time.sleep(random.uniform(0.4, 1.0))
    return body


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class BaseScraper(ABC):
    source_key: str = "custom"
    source_label: str = "Custom"

    @abstractmethod
    def matches(self, query: str, url: str | None = None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def search_url(self, query: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_products(self, html: str, page_url: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def page_urls(self, target: str, max_pages: int = 3) -> list[str]:
        """Build listing page URLs for pagination when the site supports it."""
        pages = [target]
        if not target:
            return pages
        host = domain_of(target)
        if "amazon." in host and "/s?" in target and "page=" not in target:
            for page in range(2, max_pages + 1):
                sep = "&" if "?" in target else "?"
                pages.append(f"{target}{sep}page={page}")
        elif "flipkart." in host and "page=" not in target:
            for page in range(2, max_pages + 1):
                sep = "&" if "?" in target else "?"
                pages.append(f"{target}{sep}page={page}")
        return pages

    def scrape(self, query: str, url: str | None = None, max_products: int = 48) -> list[dict[str, Any]]:
        target = url or self.search_url(query)
        max_pages = 4 if max_products > 24 else 3
        pages = self.page_urls(target, max_pages=max_pages)
        collected: list[dict[str, Any]] = []
        seen: set[str] = set()
        last_error = None
        for page_url in pages:
            try:
                html = fetch_html(page_url)
                for product in self.extract_products(html, page_url):
                    key = product.get("asin") or product.get("product_url") or product.get("title")
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    collected.append(product)
                    if len(collected) >= max_products:
                        return collected
            except Exception as exc:  # noqa: BLE001 — continue other pages; raise later if empty
                last_error = exc
        if not collected:
            if last_error:
                raise last_error
            raise NoLaptopProductsError(
                "No compatible laptop products were found on this source."
            )
        return collected[:max_products]
