"""Resolve free-text website / company / URL input to a scraper adapter.

Current product version supports Amazon only for live scraping.
Flipkart / OnePlus are recognised and return Coming Soon (not empty fake results).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from scraper.amazon_scraper import AmazonScraper
from scraper.base import ComingSoonError, UnsupportedSourceError, domain_of
from scraper.generic_scraper import GenericScraper

ACTIVE_SCRAPERS = (AmazonScraper(),)

COMING_SOON_HINTS = {
    "flipkart": "Flipkart",
    "oneplus": "OnePlus",
}


def looks_like_url(value: str) -> bool:
    text = str(value or "").strip()
    if re.match(r"^https?://", text, re.I):
        return True
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    host = (parsed.hostname or "").lower()
    return bool(host and "." in host and " " not in text)


def _coming_soon_match(query: str, url: str | None = None) -> str | None:
    text = f"{query} {url or ''}".casefold()
    host = domain_of(url) if url else ""
    if "flipkart" in text or "flipkart." in host:
        return "Flipkart"
    if "oneplus" in text or "oneplus." in host:
        return "OnePlus"
    return None


def resolve_query(raw: str) -> dict:
    """Map user input to scraper metadata. Does not perform network I/O."""
    query = str(raw or "").strip()
    if not query:
        raise ValueError("Please enter a valid website URL or supported company/source name.")

    url = None
    if looks_like_url(query):
        url = query if re.match(r"^https?://", query, re.I) else f"https://{query}"
        host = domain_of(url)
        if not host:
            raise ValueError("Please enter a valid website URL or supported company/source name.")
        for scraper in ACTIVE_SCRAPERS:
            if scraper.matches(query, url):
                return {
                    "query": query,
                    "url": url,
                    "source_key": scraper.source_key,
                    "source_label": scraper.source_label,
                    "supported": True,
                    "scraper": scraper,
                    "message": f"{scraper.source_label} source recognised.",
                }
        soon = _coming_soon_match(query, url)
        if soon:
            raise ComingSoonError(
                f"{soon} scraping is Coming Soon. Currently supported: Amazon."
            )
        raise UnsupportedSourceError(
            "This website is not currently supported for structured laptop scraping. "
            "Currently supported: Amazon."
        )

    for scraper in ACTIVE_SCRAPERS:
        if scraper.matches(query, None):
            return {
                "query": query,
                "url": scraper.search_url(query),
                "source_key": scraper.source_key,
                "source_label": scraper.source_label,
                "supported": True,
                "scraper": scraper,
                "message": f"{scraper.source_label} source recognised.",
            }

    soon = _coming_soon_match(query, None)
    if soon:
        raise ComingSoonError(
            f"{soon} scraping is Coming Soon. Currently supported: Amazon."
        )

    raise UnsupportedSourceError(
        "This website is not currently supported for structured laptop scraping. "
        "Currently supported: Amazon."
    )


def get_scraper(source_key: str):
    for scraper in ACTIVE_SCRAPERS:
        if scraper.source_key == source_key:
            return scraper
    return GenericScraper()
